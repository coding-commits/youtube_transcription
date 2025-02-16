import argparse
import sys
from urllib.parse import urlparse, parse_qs
import os
import yt_dlp


def youtube_url_processing(url):
    # Check if this is a Watch Later playlist
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    
    if 'list' in query_params and query_params['list'][0] == 'WL' and 'v' in query_params:
        # Reconstruct URL with only the video ID
        video_id = query_params['v'][0]
        return f"https://www.youtube.com/watch?v={video_id}"
    
    return url

def download_audio(url, output_dir='audio', browser=None):
    os.makedirs(output_dir, exist_ok=True)
            
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


def main():
    parser = argparse.ArgumentParser(description='YouTube Video Downloader')
    parser.add_argument('url', help='YouTube video or playlist URL')
    parser.add_argument('--browser', help='Specify the browser to use for cookies')
    args = parser.parse_args()  # Add this line to parse arguments
    
    try:
        # Check if URL is a YouTube URL
        if any(url in args.url for url in ['youtube.com', 'youtu.be']):
            url = youtube_url_processing(args.url)
            audio_files = download_audio(url, browser=args.browser)
            print(f"Audio files downloaded: {audio_files}")
        elif args.url.startswith("https://b23.tv/") or args.url.startswith("https://www.bilibili.com"):
            audio_files = download_audio(args.url, browser=args.browser)
            print(f"Audio files downloaded: {audio_files}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 