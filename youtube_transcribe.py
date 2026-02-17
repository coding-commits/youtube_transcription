import argparse
from download import download_audio
from transcribe_from_files import transcribe_from_files

def parse_args():
    parser = argparse.ArgumentParser(description='Download and transcribe YouTube videos')
    parser.add_argument('url', help='YouTube video or playlist URL')
    parser.add_argument('--browser', help='Specify the browser to use for cookies')
    parser.add_argument('--delete-after', action='store_true',
                        help='Delete audio files after transcription')
    parser.add_argument('--audio-quality', type=int, default=None,
                        help='Audio quality in kbps (defaults to original quality)')
    parser.add_argument('--sampling-rate', type=int, default=None,
                        help='Audio sampling rate in Hz (defaults to original sampling rate)')
    parser.add_argument('--model', choices=['tiny', 'base', 'small', 'medium', 'large', '4o'],
                        default='4o',
                        help='Transcription model: 4o (OpenAI gpt-4o-transcribe) or Whisper size (default: 4o)')
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Download videos
    audio_files = download_audio(
        url=args.url,
        browser=args.browser,
        sampling_rate=args.sampling_rate,
        audio_quality=args.audio_quality,
        rewrite=False
    )

    # Transcribe the downloaded files
    transcript_files = transcribe_from_files(
        audio_files,
        model_size=args.model,
        delete_after=args.delete_after,
        url=args.url
    )

    print(f"Created transcripts: {transcript_files}")

if __name__ == '__main__':
    main()
