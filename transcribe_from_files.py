import os
import sys
import argparse
import subprocess
import tempfile
import whisper
import yt_dlp
from tqdm import tqdm
from urllib.parse import urlparse, parse_qs

OPENAI_MAX_FILE_BYTES = 25 * 1024 * 1024  # 25 MB
# Chunk duration when downsize+split: mono 64k → ~0.5 MB/min; 20 min ≈ 10 MB (well under 25 MB)
OPENAI_CHUNK_DURATION_SEC = 20 * 60
OPENAI_DOWNSIZE_BITRATE = "64k"
OPENAI_DOWNSIZE_SAMPLE_RATE = 16000


def validate_cookies_file(cookies_file, browser=None):
    """Validate cookies source - either a file or browser."""
    if browser:
        # Browser specified - no need to validate file
        return cookies_file, browser
    elif cookies_file:
        # Validate file exists and is readable
        if not os.path.exists(cookies_file):
            raise ValueError(f"Cookies file not found: {cookies_file}")
        if not os.access(cookies_file, os.R_OK):
            raise ValueError(f"Cookies file is not readable: {cookies_file}")
        return cookies_file, None
    return None, None


def transcribe_audios(
        audio_files, 
        model_size='medium', 
        delete_after=False, 
        output_dir='transcripts', 
        url=None,
        whisper_prompt=None,
    ):
    """
    Transcribe audio files using Whisper and return a list of transcript file paths.
    
    Args:
        audio_files (list): List of audio file paths
        model_size (str): Whisper model size to use
        delete_after (bool): Whether to delete audio files after transcription
        output_dir (str): Directory to save transcripts
        url (str): Source URL for the audio (optional)
        whisper_prompt (str): Optional prompt for Whisper model
        
    Returns:
        list: Paths to generated transcript files
    """
    if not audio_files:
        print("No audio files provided for transcription")
        return []
    
    print(f"Loading Whisper model: {model_size}")
    model = whisper.load_model(model_size)
    
    os.makedirs(output_dir, exist_ok=True)
    
    transcript_files = []
    
    for audio_file in audio_files:
        print(f"Processing: {audio_file}")
        try:
            base_name = os.path.splitext(os.path.basename(audio_file))[0]
            transcript_file = os.path.join(output_dir, f"{base_name}.txt")
            
            if os.path.exists(transcript_file):
                print(f"Transcript already exists: {transcript_file}")
                transcript_files.append(transcript_file)
                continue
                
            abs_audio_path = os.path.abspath(audio_file)
            print(f"Starting transcription for: {audio_file}")
            
            result = model.transcribe(abs_audio_path, verbose=True, prompt=whisper_prompt)
            
            with open(transcript_file, 'w', encoding='utf-8') as f:
                if url:
                    f.write(f"source: {url}\n"+"-"*20+'\n')
                for segment in result["segments"]:
                    f.write(segment["text"].strip() + "\n")
            print(f"Transcription saved to: {transcript_file}")
            transcript_files.append(transcript_file)
            
        except Exception as e:
            print(f"Error during transcription of {audio_file}: {str(e)}")
    
    # Clean up audio files if requested
    if delete_after:
        for audio_file in audio_files:
            cleanup(audio_file)
    
    return transcript_files


def _get_audio_duration_seconds(path):
    """Return duration in seconds via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _make_openai_safe_chunks(audio_path):
    """
    Downsize and split audio into chunks under OPENAI_MAX_FILE_BYTES.
    Returns (list of temp chunk file paths, temp_dir to remove later).
    """
    duration = _get_audio_duration_seconds(audio_path)
    temp_dir = tempfile.mkdtemp(prefix="openai_chunks_")
    chunk_paths = []
    start = 0.0
    idx = 0
    while start < duration:
        end = min(start + OPENAI_CHUNK_DURATION_SEC, duration)
        out_path = os.path.join(temp_dir, f"chunk_{idx:04d}.mp3")
        cmd = [
            "ffmpeg", "-y", "-i", audio_path,
            "-ss", str(start), "-to", str(end),
            "-ac", "1", "-ar", str(OPENAI_DOWNSIZE_SAMPLE_RATE),
            "-b:a", OPENAI_DOWNSIZE_BITRATE,
            "-vn", out_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        if os.path.getsize(out_path) > OPENAI_MAX_FILE_BYTES:
            # Rare: chunk still too big; shorten and re-encode
            half = (start + end) / 2
            os.remove(out_path)
            out_path = os.path.join(temp_dir, f"chunk_{idx:04d}.mp3")
            subprocess.run([
                "ffmpeg", "-y", "-i", audio_path,
                "-ss", str(start), "-to", str(half),
                "-ac", "1", "-ar", str(OPENAI_DOWNSIZE_SAMPLE_RATE),
                "-b:a", OPENAI_DOWNSIZE_BITRATE, "-vn", out_path
            ], check=True, capture_output=True)
            chunk_paths.append(out_path)
            start = half
        else:
            chunk_paths.append(out_path)
            start = end
        idx += 1
    return chunk_paths, temp_dir


def transcribe_audios_openai(
        audio_files,
        delete_after=False,
        output_dir='transcripts',
        url=None,
):
    """
    Transcribe audio files using OpenAI gpt-4o-transcribe (API key from OPENAI_API_KEY env).
    """
    if not audio_files:
        print("No audio files provided for transcription")
        return []
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is not set. "
            "Set it to your OpenAI API key to use model_size='4o'."
        )
    try:
        from openai import OpenAI
        import httpx
    except ImportError:
        raise ImportError("Using model_size='4o' requires the openai package. Install with: pip install openai")
    # Use explicit httpx client to avoid OpenAI lib passing 'proxies' to httpx 0.28+ (TypeError)
    http_client = httpx.Client(trust_env=True)
    client = OpenAI(api_key=api_key, http_client=http_client)
    os.makedirs(output_dir, exist_ok=True)
    transcript_files = []
    for audio_file in audio_files:
        print(f"Processing: {audio_file}")
        try:
            base_name = os.path.splitext(os.path.basename(audio_file))[0]
            transcript_file = os.path.join(output_dir, f"{base_name}.txt")
            if os.path.exists(transcript_file):
                print(f"Transcript already exists: {transcript_file}")
                transcript_files.append(transcript_file)
                continue
            size = os.path.getsize(audio_file)
            abs_audio_path = os.path.abspath(audio_file)
            if size > OPENAI_MAX_FILE_BYTES:
                # Downsize and chop into shorter files, then transcribe each and concatenate
                print(f"File over 25 MB; downsize and split into chunks: {audio_file}")
                chunk_paths, temp_dir = _make_openai_safe_chunks(abs_audio_path)
                try:
                    parts = []
                    for i, chunk_path in enumerate(chunk_paths):
                        print(f"Transcribing chunk {i + 1}/{len(chunk_paths)}: {chunk_path}")
                        with open(chunk_path, "rb") as f:
                            response = client.audio.transcriptions.create(
                                model="gpt-4o-transcribe",
                                file=f,
                                response_format="text",
                            )
                        part = response if isinstance(response, str) else getattr(response, "text", str(response))
                        parts.append(part)
                    text = "\n".join(parts)
                finally:
                    for p in chunk_paths:
                        try:
                            os.remove(p)
                        except OSError:
                            pass
                    try:
                        os.rmdir(temp_dir)
                    except OSError:
                        pass
            else:
                with open(abs_audio_path, "rb") as f:
                    response = client.audio.transcriptions.create(
                        model="gpt-4o-transcribe",
                        file=f,
                        response_format="text",
                    )
                text = response if isinstance(response, str) else getattr(response, "text", str(response))
            with open(transcript_file, "w", encoding="utf-8") as f:
                if url:
                    f.write(f"source: {url}\n" + "-" * 20 + "\n")
                f.write(text)
            print(f"Transcription saved to: {transcript_file}")
            transcript_files.append(transcript_file)
        except Exception as e:
            print(f"Error during transcription of {audio_file}: {str(e)}")
    if delete_after:
        for audio_file in audio_files:
            cleanup(audio_file)
    return transcript_files


def save_transcription(text, audio_filename):
    """Save the transcription to a file."""
    # Create transcripts directory if it doesn't exist
    output_dir = 'transcripts'
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate transcript filename based on audio filename
    base_name = os.path.splitext(os.path.basename(audio_filename))[0]
    transcript_file = os.path.join(output_dir, f"{base_name}.txt")
    
    with open(transcript_file, 'w', encoding='utf-8') as f:
        f.write(text)
    return transcript_file

def cleanup(audio_file):
    """Clean up temporary audio file."""
    try:
        os.remove(audio_file)
        print(f"Cleaned up temporary file: {audio_file}")
    except Exception as e:
        print(f"Warning: Could not remove temporary file {audio_file}: {str(e)}")

def transcribe_from_videos(
        video_files, 
        model_size='medium', 
        delete_after=False, 
        output_dir='transcripts', 
        url=None,
        whisper_prompt=None
    ):
    """
    Extract audio from video files, transcribe using Whisper, and return transcript file paths.
    
    Args:
        video_files (list): List of video file paths
        model_size (str): Whisper model size to use
        delete_after (bool): Whether to delete video files after transcription
        output_dir (str): Directory to save transcripts
        url (str): Source URL for the video (optional)
        
    Returns:
        list: Paths to generated transcript files
    """
    try:
        # Create a temporary directory for extracted audio
        temp_audio_dir = os.path.join(os.path.dirname(output_dir), 'temp_audio')
        os.makedirs(temp_audio_dir, exist_ok=True)
        
        # Extract audio from videos
        audio_files = []
        for video_file in video_files:
            try:
                base_name = os.path.splitext(os.path.basename(video_file))[0]
                audio_file = os.path.join(temp_audio_dir, f"{base_name}.mp3")
                
                # Use FFmpeg to extract audio
                import subprocess
                cmd = [
                    'ffmpeg', '-i', video_file, 
                    '-q:a', '0', '-map', 'a', 
                    '-vn', audio_file, 
                    '-y'  # Overwrite if exists
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                audio_files.append(audio_file)
                print(f"Extracted audio from {video_file} to {audio_file}")
                
            except Exception as e:
                print(f"Error extracting audio from {video_file}: {str(e)}")
        
        # Transcribe the extracted audio files
        if model_size == "4o":
            transcript_files = transcribe_audios_openai(
                audio_files=audio_files,
                delete_after=True,
                output_dir=output_dir,
                url=url,
            )
        else:
            transcript_files = transcribe_audios(
                audio_files=audio_files,
                model_size=model_size,
                delete_after=True,  # Always delete temporary audio files
                output_dir=output_dir,
                url=url,
                whisper_prompt=whisper_prompt
            )
        
        # Delete original video files if requested
        if delete_after:
            for video_file in video_files:
                cleanup(video_file)
        
        # Clean up temporary audio directory if empty
        try:
            if not os.listdir(temp_audio_dir):
                os.rmdir(temp_audio_dir)
        except:
            pass
            
        return transcript_files
        
    except Exception as e:
        print(f"Error in video transcription: {str(e)}")
        return []

def transcribe_from_files(files, model_size='4o', delete_after=False, output_dir='transcripts', url=None, whisper_prompt=None):
    """
    Main function to be called from other scripts.
    Routes files to appropriate transcription function based on file extension.
    
    Args:
        files (list): List of file paths (audio or video)
        model_size (str): '4o' for OpenAI gpt-4o-transcribe, or Whisper size: tiny, base, small, medium, large
        delete_after (bool): Whether to delete files after transcription
        output_dir (str): Directory to save transcripts
        url (str): Source URL for the files (optional)
        whisper_prompt (str): Optional prompt for Whisper model (ignored when model_size='4o')
        
    Returns:
        list: Paths to generated transcript files
    """
    if not files:
        print("No files provided for transcription")
        return []
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Separate files by type
    audio_extensions = ['.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg']
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.m4v']
    
    audio_files = []
    video_files = []
    unknown_files = []
    
    for file in files:
        ext = os.path.splitext(file)[1].lower()
        if ext in audio_extensions:
            audio_files.append(file)
        elif ext in video_extensions:
            video_files.append(file)
        else:
            unknown_files.append(file)
    
    if unknown_files:
        print(f"Warning: Unsupported file types: {unknown_files}")
    
    # Process files by type
    transcript_files = []
    
    if audio_files:
        print(f"Processing {len(audio_files)} audio files...")
        if model_size == "4o":
            audio_transcripts = transcribe_audios_openai(
                audio_files=audio_files,
                delete_after=delete_after,
                output_dir=output_dir,
                url=url,
            )
        else:
            audio_transcripts = transcribe_audios(
                audio_files=audio_files,
                model_size=model_size,
                delete_after=delete_after,
                output_dir=output_dir,
                url=url,
                whisper_prompt=whisper_prompt
            )
        transcript_files.extend(audio_transcripts)
    
    if video_files:
        print(f"Processing {len(video_files)} video files...")
        video_transcripts = transcribe_from_videos(
            video_files=video_files,
            model_size=model_size,
            delete_after=delete_after,
            output_dir=output_dir,
            url=url,
            whisper_prompt=whisper_prompt
        )
        transcript_files.extend(video_transcripts)
    
    return transcript_files

def main():
    parser = argparse.ArgumentParser(description='Audio Transcription Tool')
    parser.add_argument('files', nargs='+', help='Paths to audio or video files')
    parser.add_argument('--model', choices=['tiny', 'base', 'small', 'medium', 'large', '4o'],
                        default='4o', help='Transcription model: 4o (OpenAI gpt-4o-transcribe) or Whisper size')
    parser.add_argument('--delete-audio', action='store_true', 
                        help='Delete audio files after transcription')
    parser.add_argument('--audio-dir', default='audio',
                        help='Directory containing audio files (default: audio)')
    parser.add_argument('--output-dir', default='transcripts',
                        help='Directory for transcript files (default: transcripts)')
    parser.add_argument('--whisper-prompt', default=None,
                        help='Whisper prompt to use for transcription')
    
    args = parser.parse_args()
    
    try:
        # Use the file paths as provided by the user
        # This allows both absolute paths and paths relative to the current directory
        file_paths = args.files
        
        transcript_files = transcribe_from_files(
            files=file_paths,
            model_size=args.model,
            delete_after=args.delete_audio,
            output_dir=args.output_dir
        )
        print(f"Transcription completed. Files created: {transcript_files}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 