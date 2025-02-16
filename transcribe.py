import os
import sys
import argparse
import whisper
import yt_dlp
from tqdm import tqdm
from urllib.parse import urlparse, parse_qs

def validate_url(url):
    """
    Validate if the provided URL is a valid YouTube URL.
    If URL contains a WL (Watch Later) playlist, extract only the video ID.
    """
    if not url.startswith(('https://www.youtube.com/', 'https://youtu.be/', 'www.youtube.com/')):
        raise ValueError("Invalid YouTube URL. Please provide a valid YouTube URL.")
    
    # Check if this is a Watch Later playlist
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    
    if 'list' in query_params and query_params['list'][0] == 'WL' and 'v' in query_params:
        # Reconstruct URL with only the video ID
        video_id = query_params['v'][0]
        return f"https://www.youtube.com/watch?v={video_id}"
    
    return url

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

def download_audio(url, output_dir='audio', cookies_file='cookies.txt', browser=None):
    """Download audio from YouTube video."""
    os.makedirs(output_dir, exist_ok=True)
        
    cookies_file, browser = validate_cookies_file(cookies_file, browser)
        
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '32',
        }],
        'postprocessor_args': {
            'ffmpeg': ['-ar', '16000'],  # Arguments for FFmpeg
        },
        'outtmpl': os.path.join(output_dir, '%(title).25s-%(id).10s.%(ext)s'),
        'progress_hooks': [lambda d: print(f"Downloading: {d['_percent_str']} of {d['_total_bytes_str']}") if d['status'] == 'downloading' else None],
        'cookiesfile': cookies_file if cookies_file else None,
        'cookiesfrombrowser': (browser,) if browser else None,
        'restrictfilenames': False,    # Must be False to preserve Chinese characters
        'windowsfilenames': True,   
        'replace_spaces': True,       
        'ignoreerrors': True,          # Continue on download errors
        'clean_infojson': True       
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_files = []
            
            videos_info = info['entries'] if 'entries' in info else [info]
            
            for video_info in videos_info:
                # Let yt-dlp handle the filename creation
                filename = ydl.prepare_filename(video_info)
                # Replace the extension with mp3 since we're converting
                filename = os.path.splitext(filename)[0] + '.mp3'
                print(filename)
                full_path = os.path.abspath(filename)
                
                if os.path.exists(full_path):
                    print(f"Audio file already exists: {full_path}")
                    audio_files.append(full_path)
                    continue
                    
                print(f"Downloading audio for: {video_info['title']}")
                ydl.download([video_info['webpage_url']])
                audio_files.append(full_path)
            
            return audio_files
    except Exception as e:
        raise Exception(f"Error downloading audio: {str(e)}")

def transcribe_audios(audio_files, model_size='medium'):
    """Transcribe the audio files using Whisper and save the transcriptions to transcripts/ directory."""
    print(f"Loading Whisper model: {model_size}")
    model = whisper.load_model(model_size)
    
    # Create transcripts directory
    output_dir = 'transcripts'
    os.makedirs(output_dir, exist_ok=True)
    
    for audio_file in audio_files:
        print(f"Processing: {audio_file}")
        try:
            # Generate expected transcript filename
            base_name = os.path.splitext(os.path.basename(audio_file))[0]
            transcript_file = os.path.join(output_dir, f"{base_name}.txt")
            
            # Check if transcript already exists
            if os.path.exists(transcript_file):
                print(f"Transcript already exists: {transcript_file}")
                continue
                
            # Convert to absolute path to handle spaces correctly
            abs_audio_path = os.path.abspath(audio_file)
            print(f"Starting transcription for: {audio_file}")
            
            # Perform transcription
            result = model.transcribe(abs_audio_path, verbose=False)
            
            # Save transcription immediately
            with open(transcript_file, 'w', encoding='utf-8') as f:
                f.write(result["text"])
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

def main():
    parser = argparse.ArgumentParser(description='YouTube Video Transcription Tool')
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('--model', choices=['tiny', 'base', 'small', 'medium', 'large'], 
                        default='medium', help='Whisper model size')
    parser.add_argument('--delete-audio', action='store_true', 
                        help='Delete the downloaded audio file after transcription')
    parser.add_argument('--cookies', default='cookies.txt',
                        help='Path to cookies file for authenticated access. Must be in Netscape/Mozilla format.')
    parser.add_argument('--browser', choices=['chrome', 'firefox', 'opera', 'edge', 'safari', 'chromium'],
                        help='Extract cookies from specified browser')
    
    args = parser.parse_args()
    
    try:
        url = validate_url(args.url)
        
        # Download audio to audio/ directory
        print("Downloading audio...")
        audio_files = download_audio(url, cookies_file=args.cookies, browser=args.browser)
        print(f"Audio files downloaded: {audio_files}")
        
        # Transcribe
        print("Transcribing audio...")
        transcribe_audios(audio_files, args.model)
        
        # Cleanup
        if args.delete_audio:
            for audio_file in audio_files:
                cleanup(audio_file)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
"""
    # test case 1: single video: 
python transcribe.py "https://www.youtube.com/watch?v=RnPJJ7EObPs"
    # test case 2: play list: 
python transcribe.py "https://www.youtube.com/watch?v=RnPJJ7EObPs&list=PLkWPSiGw7vLJid9ZLSxKZwNms-pIam4Pt"
    # test case 3: cookies: 
python transcribe.py "https://www.youtube.com/watch?v=duScLCF1eIw"
    # test case 4: chinese:
python transcribe.py "https://www.youtube.com/watch?v=mkcGlF3oobc"
    # test case 5: ignore WL:
python transcribe.py "https://www.youtube.com/watch?v=YE24Rpn3oD0&list=WL&index=8"

"""