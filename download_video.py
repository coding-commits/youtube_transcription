"""
Usage:
source whisper-env/bin/activate
cd distribute
python download_video.py "https://www.youtube.com/watch?v=..."
"""

import argparse
import os
import sys
from urllib.parse import parse_qs, urlparse

import yt_dlp


def is_bilibili_url(url: str) -> bool:
    """Return True if the URL looks like a Bilibili URL (including b23.tv short links)."""
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        return host == "b23.tv" or host.endswith(".b23.tv") or host.endswith("bilibili.com")
    except Exception:
        return False


def youtube_url_processing(url: str) -> str:
    """Normalize certain YouTube URLs (e.g., Watch Later) to a stable watch URL."""
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    # Watch Later playlist entries can be passed as watch?v=...&list=WL; keep only v=...
    if "list" in query_params and query_params["list"][0] == "WL" and "v" in query_params:
        video_id = query_params["v"][0]
        return f"https://www.youtube.com/watch?v={video_id}"

    return url


def download_video(
    url: str,
    output_dir: str = "video",
    browser: str | None = None,
    rewrite: bool = True,
    max_list_len: int = 50,
    video_format: str | None = None,
    merge_output_format: str = "mp4",
) -> list[str]:
    """Download full video (video+audio) from a video/playlist URL.

    Args:
        url: YouTube or Bilibili video/playlist URL.
        output_dir: Directory to save videos (default: 'video').
        browser: Browser name to use for cookies via yt-dlp (default: None).
        rewrite: Whether to rewrite existing files (default: True).
        max_list_len: Maximum number of videos to download from playlist (default: 50).
        video_format: Optional yt-dlp format selector override.
        merge_output_format: Container format for merged output (default: 'mp4').

    Returns:
        List of absolute paths to downloaded video files.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Sensible default for full video downloads.
    # - Prefer separate video+audio when possible, fall back to 'best'.
    # - On some sites, 'bestvideo+bestaudio' may not be available; yt-dlp will fall back.
    format_selector = video_format or "bestvideo+bestaudio/best"

    ydl_opts: dict = {
        "format": format_selector,
        "merge_output_format": merge_output_format,
        "outtmpl": os.path.join(output_dir, "%(title).25s-%(id).10s.%(ext)s"),
        "progress_hooks": [
            lambda d: print(
                f"Downloading: {d.get('_percent_str', '0%')} of {d.get('_total_bytes_str', 'unknown')}"
            )
            if d.get("status") == "downloading"
            else None
        ],
        "cookiesfrombrowser": (browser,) if browser else None,
        "restrictfilenames": False,  # Must be False to preserve Chinese characters
        "windowsfilenames": True,
        "replace_spaces": True,
        "ignoreerrors": True,  # Continue on download errors in playlists
        "clean_infojson": True,
        "playlistend": max_list_len,
        "extractor_args": {
            "youtube": {
                "player_client": ["tv", "web", "mweb"],
            }
        },
        "check_formats": True,
        "js_runtimes": {"node": {}},
        "remote_components": ["ejs:github"],
    }

    try:
        with yt_dlp.YoutubeDL(params=ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                raise Exception(
                    "Failed to extract video information. This might be due to site blocking or invalid cookies."
                )

            videos_info = (
                [v for v in info.get("entries", []) if v is not None] if "entries" in info else [info]
            )

            downloaded_files: list[str] = []
            for video_info in videos_info:
                try:
                    filename = ydl.prepare_filename(video_info)
                    full_path = os.path.abspath(filename)

                    if os.path.exists(full_path) and not rewrite:
                        print(f"Video file already exists: {full_path}")
                        downloaded_files.append(full_path)
                        continue

                    print(f"Downloading video for: {video_info.get('title', 'Unknown Title')}")
                    download_url = video_info.get("webpage_url") or url
                    ydl.download([download_url])

                    # After merge, the extension can change; try to locate the merged output.
                    base_no_ext = os.path.splitext(full_path)[0]
                    candidate_paths = [
                        full_path,
                        base_no_ext + "." + merge_output_format,
                    ]
                    found = next((p for p in candidate_paths if os.path.exists(p)), None)
                    if found:
                        downloaded_files.append(os.path.abspath(found))
                    else:
                        print(f"Warning: Could not find expected video file near {full_path}")
                except Exception as ve:
                    print(f"Error processing video {video_info.get('title', 'unknown')}: {str(ve)}")
                    continue

            if not downloaded_files:
                raise Exception("No video files were successfully downloaded.")

            return downloaded_files
    except Exception as e:
        raise Exception(f"Error downloading video: {str(e)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Video Downloader (YouTube/Bilibili)")
    parser.add_argument("url", help="YouTube/Bilibili video or playlist URL")
    parser.add_argument("--browser", help="Specify the browser to use for cookies")
    parser.add_argument(
        "--format",
        dest="video_format",
        default=None,
        help="yt-dlp format selector override (default: bestvideo+bestaudio/best)",
    )
    parser.add_argument(
        "--merge-output-format",
        default="mp4",
        help="Container format for merged output (default: mp4)",
    )
    parser.add_argument(
        "--no-rewrite",
        action="store_true",
        help="Do not rewrite existing files (default: False)",
    )
    parser.add_argument(
        "--max-list-len",
        type=int,
        default=50,
        help="Maximum number of videos to download from playlist (default: 50)",
    )
    parser.add_argument(
        "--output-dir",
        default="video",
        help="Directory to save videos (default: video)",
    )
    args = parser.parse_args()

    try:
        url = args.url
        if any(host in url for host in ["youtube.com", "youtu.be"]):
            url = youtube_url_processing(url)

        video_files = download_video(
            url=url,
            output_dir=args.output_dir,
            browser=args.browser,
            rewrite=not args.no_rewrite,
            max_list_len=args.max_list_len,
            video_format=args.video_format,
            merge_output_format=args.merge_output_format,
        )
        print(f"Video files downloaded: {video_files}")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

