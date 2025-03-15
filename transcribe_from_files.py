import os
import sys
import argparse
import whisper
import yt_dlp
from tqdm import tqdm
from urllib.parse import urlparse, parse_qs


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


def transcribe_audios(audio_files, model_size='medium', output_dir='transcripts', url=None):
    """Transcribe the audio files using Whisper and save the transcriptions to specified directory."""
    print(f"Loading Whisper model: {model_size}")
    model = whisper.load_model(model_size)
    
    os.makedirs(output_dir, exist_ok=True)
    
    for audio_file in audio_files:
        print(f"Processing: {audio_file}")
        try:
            base_name = os.path.splitext(os.path.basename(audio_file))[0]
            transcript_file = os.path.join(output_dir, f"{base_name}.txt")
            
            if os.path.exists(transcript_file):
                print(f"Transcript already exists: {transcript_file}")
                continue
                
            abs_audio_path = os.path.abspath(audio_file)
            print(f"Starting transcription for: {audio_file}")
            
            result = model.transcribe(abs_audio_path, verbose=True)
            
            with open(transcript_file, 'w', encoding='utf-8') as f:
                if url:
                    f.write(f"source: {url}\n"+"-"*20+'\n')
                for segment in result["segments"]:
                    f.write(segment["text"] + "\n")
            print(f"Transcription saved to: {transcript_file}")
            
        except Exception as e:
            print(f"Error during transcription of {audio_file}: {str(e)}")

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

def transcribe_from_audios(audio_files, model_size='medium', delete_after=False, output_dir='transcripts', url=None):
    """
    Transcribe audio files using Whisper and return a list of transcript file paths.
    
    Args:
        audio_files (list): List of audio file paths
        model_size (str): Whisper model size to use
        delete_after (bool): Whether to delete audio files after transcription
        output_dir (str): Directory to save transcripts
        url (str): Source URL for the audio (optional)
        
    Returns:
        list: Paths to generated transcript files
    """
    try:
        transcribe_audios(audio_files, model_size, output_dir, url)
        
        if delete_after:
            for audio_file in audio_files:
                cleanup(audio_file)
                
        transcript_files = []
        for audio_file in audio_files:
            base_name = os.path.splitext(os.path.basename(audio_file))[0]
            transcript_file = os.path.join(output_dir, f"{base_name}.txt")
            if os.path.exists(transcript_file):
                transcript_files.append(transcript_file)
        
        return transcript_files
        
    except Exception as e:
        print(f"Error in audio transcription: {str(e)}")
        return []

def transcribe_from_videos(video_files, model_size='medium', delete_after=False, output_dir='transcripts', url=None):
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
        transcript_files = transcribe_from_audios(
            audio_files=audio_files,
            model_size=model_size,
            delete_after=True,  # Always delete temporary audio files
            output_dir=output_dir,
            url=url
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

def transcribe_from_files(files, model_size='medium', delete_after=False, output_dir='transcripts', url=None):
    """
    Main function to be called from other scripts.
    Routes files to appropriate transcription function based on file extension.
    
    Args:
        files (list): List of file paths (audio or video)
        model_size (str): Whisper model size to use
        delete_after (bool): Whether to delete files after transcription
        output_dir (str): Directory to save transcripts
        url (str): Source URL for the files (optional)
        
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
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']
    
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
        audio_transcripts = transcribe_from_audios(
            audio_files=audio_files,
            model_size=model_size,
            delete_after=delete_after,
            output_dir=output_dir,
            url=url
        )
        transcript_files.extend(audio_transcripts)
    
    if video_files:
        print(f"Processing {len(video_files)} video files...")
        video_transcripts = transcribe_from_videos(
            video_files=video_files,
            model_size=model_size,
            delete_after=delete_after,
            output_dir=output_dir,
            url=url
        )
        transcript_files.extend(video_transcripts)
    
    return transcript_files

def main():
    parser = argparse.ArgumentParser(description='Audio Transcription Tool')
    parser.add_argument('files', nargs='+', help='Paths to audio or video files')
    parser.add_argument('--model', choices=['tiny', 'base', 'small', 'medium', 'large'], 
                        default='medium', help='Whisper model size')
    parser.add_argument('--delete-audio', action='store_true', 
                        help='Delete audio files after transcription')
    parser.add_argument('--audio-dir', default='audio',
                        help='Directory containing audio files (default: audio)')
    parser.add_argument('--output-dir', default='transcripts',
                        help='Directory for transcript files (default: transcripts)')
    
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