# YouTube Audio Transcription Tool

This tool automates the process of transcribing YouTube content by downloading videos' audio tracks and converting them to text using OpenAI's Whisper model running locally. The resulting transcriptions are saved as text files, which can then be further analyzed using ChatGPT or other tools.

## Requirements

- Python 3.8 or higher
- FFmpeg (required for audio processing)

## Installation

1. Create a virtual environment:
```bash
python -m venv whisper-env
source whisper-env/bin/activate  # On Mac/Linux
# OR
whisper-env\Scripts\activate     # On Windows
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

Downlaod and transcribe:
```bash
python youtube_transcribe.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Advanced options:
```bash
python transcribe.py "https://www.youtube.com/watch?v=VIDEO_ID" [OPTIONS]

Options:
  --delete-audio                          Delete audio files after transcription
  --browser {chrome,firefox,opera,edge,safari,chromium}
                                         Extract cookies from specified browser
```


Downlaod only:
```bash
python download.py "https://www.youtube.com/watch?v=VIDEO_ID"
```


Downlaod with low quality for transcription:
```bash
python download.py "https://www.youtube.com/watch?v=VIDEO_ID" --audio-quality 32 --sample-rate 16000
```

The tool supports:
- Youtube single video URLs
- Youtube playlist URLs (except Watch Later playlists)
- Videos requiring authentication (via cookies file or browser cookies)
- Videos with non-ASCII titles (including Chinese characters)

Downloaded audio files are saved in the `audio/` directory, and transcriptions are saved in the `transcripts/` directory.
