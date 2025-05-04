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

def download_audio(url, output_dir='audio', browser=None, sampling_rate=None, 
                  audio_quality='', rewrite=True, max_list_len=50):
    """Download audio from a video URL.
    
    Args:
        url (str): YouTube or Bilibili video/playlist URL
        output_dir (str): Directory to save audio files (default: 'audio')
        browser (str): Browser to use for cookies (default: None)
        sampling_rate (int): Audio sampling rate in Hz (default: None)
        audio_quality (str): Audio quality in kbps (default: '')
        rewrite (bool): Whether to rewrite existing files (default: True)
        max_downloads (int): Maximum number of videos to download from playlist (default: 50)
        
    Returns:
        list: Paths to downloaded audio files
        
    Raises:
        Exception: If download fails
    """
    os.makedirs(output_dir, exist_ok=True)
            
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': audio_quality
        }],
        'outtmpl': os.path.join(output_dir, '%(title).25s-%(id).10s.%(ext)s'),
        'progress_hooks': [lambda d: print(f"Downloading: {d['_percent_str']} of {d['_total_bytes_str']}") if d['status'] == 'downloading' else None],
        'cookiesfrombrowser': (browser,) if browser else None,
        'restrictfilenames': False,    # Must be False to preserve Chinese characters
        'windowsfilenames': True,   
        'replace_spaces': True,       
        'ignoreerrors': True,          # Continue on download errors
        'clean_infojson': True,
        'playlistend':max_list_len
    }

    if sampling_rate:
        ydl_opts['postprocessor_args'] = {'ffmpeg': ['-ar', str(sampling_rate)]}
    if audio_quality:
        ydl_opts['postprocessor_args']['preferredquality'] = str(audio_quality)
    
    try:
        with yt_dlp.YoutubeDL(params = ydl_opts) as ydl:

            info = ydl.extract_info(url, download=False)
            audio_files = []
            

            videos_info = info['entries'] if 'entries' in info else [info]
            
            for video_info in videos_info:
                filename = ydl.prepare_filename(video_info)
                filename = os.path.splitext(filename)[0] + '.mp3'
                print(filename)
                full_path = os.path.abspath(filename)
                
                if os.path.exists(full_path) and not rewrite:
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
    parser.add_argument('--sampling-rate', type=int, default=None, help='Audio sampling rate in Hz (default: 16000)')
    parser.add_argument('--audio-quality', type=str, default=None, 
                       help='Audio quality in kbps (default: 32). Common values: 32, 64, 96, 128, 192, 256, 320')
    parser.add_argument('--no-rewrite', action='store_true', 
                       help='Do not rewrite existing files (default: False)')
    parser.add_argument('--max-list-len', type=int, default=50, 
                       help='Maximum number of videos to download from playlist (default: 50)')
    args = parser.parse_args()
    
    max_list_len = args.max_list_len
    try:
        # Check if URL is a YouTube URL
        if any(url in args.url for url in ['youtube.com', 'youtu.be']):
            url = youtube_url_processing(args.url)
            audio_files = download_audio(url, browser=args.browser, sampling_rate=args.sampling_rate, 
                                      audio_quality=args.audio_quality, rewrite=not args.no_rewrite,
                                      max_list_len=max_list_len)
            print(f"Audio files downloaded: {audio_files}")
        elif args.url.startswith("https://b23.tv/") or args.url.startswith("https://www.bilibili.com"):
            audio_files = download_audio(args.url, browser=args.browser, sampling_rate=args.sampling_rate, 
                                      audio_quality=args.audio_quality, rewrite=not args.no_rewrite,
                                      max_list_len=max_list_len)
            print(f"Audio files downloaded: {audio_files}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 