import argparse
from download import download_from_youtube
from transcribe import transcribe_from_files

def parse_args():
    parser = argparse.ArgumentParser(description='Download and transcribe YouTube videos')
    parser.add_argument('url', help='YouTube video or playlist URL')
    parser.add_argument('--model-size', default='medium', choices=['tiny', 'base', 'small', 'medium', 'large'],
                        help='Whisper model size (default: medium)')
    parser.add_argument('--delete-after', action='store_true',
                        help='Delete audio files after transcription')
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Download videos
    audio_files = download_from_youtube(
        url=args.url
    )

    # Transcribe the downloaded files
    transcript_files = transcribe_from_files(
        audio_files=audio_files,
        model_size=args.model_size,
        delete_after=args.delete_after
    )

    print(f"Created transcripts: {transcript_files}")

if __name__ == '__main__':
    main()


"""
source whisper-env/bin/activate
    # test case 1: single video: 
python youtube_transcribe.py "https://www.youtube.com/watch?v=RnPJJ7EObPs"
    # test case 2: play list: 
python youtube_transcribe.py "https://www.youtube.com/watch?v=RnPJJ7EObPs&list=PLkWPSiGw7vLJid9ZLSxKZwNms-pIam4Pt"
    # test case 3: cookies: 
python youtube_transcribe.py "https://www.youtube.com/watch?v=duScLCF1eIw" --browser edge
    # test case 4: chinese:
python youtube_transcribe.py "https://www.youtube.com/watch?v=mkcGlF3oobc"
    # test case 5: ignore WL:
python youtube_transcribe.py "https://www.youtube.com/watch?v=YE24Rpn3oD0&list=WL&index=8"

"""