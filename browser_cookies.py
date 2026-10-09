"""Shared browser-cookie checks for the download scripts."""

import os
import sys


def _chrome_cookie_dir():
    return os.path.expanduser('~/Library/Application Support/Google/Chrome')


def ensure_browser_cookies_readable(browser):
    """Fail early when macOS hides the Chrome cookie database.

    yt-dlp walks that folder and, on PermissionError, reports that the
    cookies database is missing.
    """
    if not browser or browser.lower() != 'chrome' or sys.platform != 'darwin':
        return
    cookie_dir = _chrome_cookie_dir()
    try:
        os.listdir(cookie_dir)
    except FileNotFoundError:
        raise Exception(
            f"Chrome cookie folder not found: {cookie_dir}. "
            "Install Chrome or pass a browser that is installed."
        )
    except PermissionError:
        raise Exception(
            "macOS blocked access to Chrome cookies "
            f"({cookie_dir}). Enable Full Disk Access for this terminal "
            "(System Settings → Privacy & Security → Full Disk Access), "
            "then quit and reopen the terminal and run the command again."
        )
