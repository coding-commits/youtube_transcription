import argparse
from download import download_audio
from transcribe import transcribe_from_files

def parse_args():
    parser = argparse.ArgumentParser(description='Download and transcribe YouTube videos')
    parser.add_argument('url', help='YouTube video or playlist URL')
    parser.add_argument('--browser', help='Specify the browser to use for cookies')
    parser.add_argument('--delete-after', action='store_true',
                        help='Delete audio files after transcription')
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Download videos
    audio_files = download_audio(
        url=args.url,
        browser=args.browser,
        sample_rate=16000,
        audio_quality=32,
        rewrite=False
    )

    # Transcribe the downloaded files
    transcript_files = transcribe_from_files(
        audio_files=audio_files,
        model_size='medium',
        delete_after=args.delete_after,
        url = args.url
    )

    print(f"Created transcripts: {transcript_files}")

if __name__ == '__main__':
    main()
