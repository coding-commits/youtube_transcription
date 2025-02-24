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

def transcribe_from_files(audio_files, model_size='medium', delete_after=False, output_dir='transcripts', url=None):
    """
    Main function to be called from other scripts.
    Returns a list of transcript file paths.
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
        print(f"Error in transcription: {str(e)}")
        return []

def main():
    parser = argparse.ArgumentParser(description='Audio Transcription Tool')
    parser.add_argument('files', nargs='+', help='Paths to audio files')
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
        # Construct full paths for audio files
        audio_files = [os.path.join(args.audio_dir, f) for f in args.files]
        
        transcript_files = transcribe_from_files(
            audio_files=audio_files,
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