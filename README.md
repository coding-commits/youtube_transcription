# YouTube Audio Transcription Tool

This tool automates the process of transcribing YouTube content by downloading videos' audio tracks and converting them to text using OpenAI's Whisper model running locally. The resulting transcriptions are saved as text files, which can then be further analyzed using ChatGPT or other tools.

Update 2025-04: You can use this tool for the purpose of [just downloading](#download-only) the audio as well.

## Requirements

- Python 3.8 or higher
- FFmpeg (required for audio processing)

## Before you start

1. Create and activate a virtual environment:

**Mac/Linux**
```bash
python -m venv whisper-env
source whisper-env/bin/activate
```

**Windows**
```bash
python -m venv whisper-env
whisper-env\Scripts\activate
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

## Transcription

Downlaod and transcribe:
```bash
python youtube_transcribe.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Advanced options:
```bash
python youtube_transcribe.py "https://www.youtube.com/watch?v=VIDEO_ID" [OPTIONS]

Options:
  --browser {chrome,firefox,opera,edge,safari,chromium}
              Uses cookies from specified browser, for paid content
  --delete-after                    Delete audio files after transcription
```


## Download only
```bash
python download.py "https://www.youtube.com/watch?v=VIDEO_ID"
```


## Download with low quality
```bash
python download.py "https://www.youtube.com/watch?v=VIDEO_ID" --audio-quality 32 --sampling-rate 16000
```

The tool supports:
- Youtube single video URLs
- Youtube playlist URLs (except Watch Later playlists)
- Videos requiring authentication (via cookies file or browser cookies)
- Videos with non-ASCII titles (including Chinese characters)

Downloaded audio files are saved in the `audio/` directory, and transcriptions are saved in the `transcripts/` directory.
