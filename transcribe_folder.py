#!/usr/bin/env python3
"""
Transcribe a folder of audio/video files using Whisper.

This script processes all supported audio and video files in a specified directory
and generates transcriptions for each file.
"""

import os
import sys
import argparse
import glob
from pathlib import Path
from transcribe_from_files import transcribe_from_files


def get_supported_files(folder_path):
    """
    Get all supported audio and video files from the specified folder.
    
    Args:
        folder_path (str): Path to the folder containing audio/video files
        
    Returns:
        list: List of file paths for supported audio/video files
    """
    # Supported file extensions
    audio_extensions = ['*.mp3', '*.wav', '*.m4a', '*.flac', '*.aac', '*.ogg']
    video_extensions = ['*.mp4', '*.avi', '*.mov', '*.mkv', '*.webm', '*.flv']
    
    all_extensions = audio_extensions + video_extensions
    
    supported_files = []
    
    # Convert folder path to Path object for easier handling
    folder = Path(folder_path)
    
    if not folder.exists():
        raise ValueError(f"Folder does not exist: {folder_path}")
    
    if not folder.is_dir():
        raise ValueError(f"Path is not a directory: {folder_path}")
    
    # Find all files with supported extensions
    for extension in all_extensions:
        pattern = folder / extension
        files = glob.glob(str(pattern), recursive=False)
        supported_files.extend(files)
    
    # Also check for files with uppercase extensions
    for extension in all_extensions:
        pattern = folder / extension.upper()
        files = glob.glob(str(pattern), recursive=False)
        supported_files.extend(files)
    
    # Remove duplicates and sort
    supported_files = sorted(list(set(supported_files)))
    
    return supported_files


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Transcribe all audio/video files in a folder using Whisper'
    )
    parser.add_argument(
        '--path', 
        required=True,
        help='Path to folder containing audio/video files'
    )
    parser.add_argument(
        '--model', 
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        default='large',
        help='Whisper model size to use (default: large)'
    )
    parser.add_argument(
        '--audio-quality', 
        type=int,
        default=32,
        help='Audio quality in kbps (default: 32)'
    )
    parser.add_argument(
        '--sampling-rate', 
        type=int,
        default=16000,
        help='Audio sampling rate in Hz (default: 16000)'
    )
    parser.add_argument(
        '--delete-after', 
        action='store_true',
        help='Delete original files after transcription'
    )
    parser.add_argument(
        '--output-dir', 
        default='transcripts',
        help='Directory to save transcript files (default: transcripts)'
    )
    parser.add_argument(
        '--recursive', 
        action='store_true',
        help='Search for files recursively in subdirectories'
    )
    
    return parser.parse_args()


def main():
    """Main function to transcribe files in a folder."""
    args = parse_args()
    
    try:
        # Get all supported files from the folder
        print(f"Scanning folder: {args.path}")
        supported_files = get_supported_files(args.path)
        
        if not supported_files:
            print(f"No supported audio/video files found in: {args.path}")
            print("Supported formats: mp3, wav, m4a, flac, aac, ogg, mp4, avi, mov, mkv, webm, flv")
            return
        
        print(f"Found {len(supported_files)} supported files:")
        for file in supported_files:
            print(f"  - {os.path.basename(file)}")
        
        # Process the files using the existing transcribe_from_files function
        print(f"\nStarting transcription with model: {args.model}")
        print(f"Audio quality: {args.audio_quality} kbps")
        print(f"Sampling rate: {args.sampling_rate} Hz")
        
        transcript_files = transcribe_from_files(
            files=supported_files,
            model_size=args.model,
            delete_after=args.delete_after,
            output_dir=args.path + "/transcripts" 
        )
        
        print(f"\nTranscription completed!")
        print(f"Generated {len(transcript_files)} transcript files:")
        for transcript in transcript_files:
            print(f"  - {transcript}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
