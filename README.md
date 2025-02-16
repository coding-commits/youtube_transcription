# YouTube Audio Transcription Tool

This tool downloads audio from YouTube videos and transcribes them using OpenAI's Whisper model locally.
The output is a text file with the transcription. And you can upload it to chatGPT to extract knowledge out of it.

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

Basic usage:
```bash
python transcribe.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Advanced options:
```bash
python transcribe.py "https://www.youtube.com/watch?v=VIDEO_ID" [OPTIONS]

Options:
  --model {tiny,base,small,medium,large}  Whisper model size (default: medium)
  --delete-audio                          Delete audio files after transcription
  --browser {chrome,firefox,opera,edge,safari,chromium}
                                         Extract cookies from specified browser
```

The tool supports:
- Single video URLs
- Playlist URLs (except Watch Later playlists)
- Videos requiring authentication (via cookies file or browser cookies)
- Videos with non-ASCII titles (including Chinese characters)

Downloaded audio files are saved in the `audio/` directory, and transcriptions are saved in the `transcripts/` directory.

## Model Sizes

- `tiny`: Fastest, least accurate
- `base`: Fast, acceptable accuracy
- `small`: Balanced speed/accuracy
- `medium`: Good accuracy (default)
- `large`: Best accuracy, slowest

## Output

The transcription will be saved to `transcription.txt` by default, or to the specified output file. The downloaded audio file will be deleted unless the `--keep-audio` flag is used. 