"""
upload_youtube.py
Uploads the processed video + thumbnail to YouTube via the Data API v3.
Uses OAuth2 credentials stored as GitHub Secrets.
"""

import os
import json
import time
import logging
import tempfile
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

log = logging.getLogger("yt-uploader")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

# Category IDs
CATEGORY_MUSIC = "10"

# Privacy: "public", "unlisted", "private"
# Start with "public" — change to "unlisted" for testing
PRIVACY_STATUS = os.environ.get("VIDEO_PRIVACY", "public")


def _get_credentials() -> Credentials:
    """
    Load credentials from environment variables (GitHub Secrets).
    Expected env vars:
      YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
    """
    client_id     = os.environ["YT_CLIENT_ID"]
    client_secret = os.environ["YT_CLIENT_SECRET"]
    refresh_token = os.environ["YT_REFRESH_TOKEN"]

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

    # Force refresh to get a valid access token
    creds.refresh(Request())
    return creds


def upload_to_youtube(
    video_path: str,
    thumbnail_path: str,
    title: str,
    description: str,
    tags: list[str],
) -> str:
    """
    Uploads video and sets thumbnail.
    Returns the public YouTube URL.
    """
    creds   = _get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    # ── Upload video ─────────────────────────────────────────────────
    log.info(f"  Uploading: {Path(video_path).name} ({Path(video_path).stat().st_size / (1024*1024):.1f} MB)")

    body = {
        "snippet": {
            "title":       title[:100],
            "description": description,
            "tags":        tags[:500],           # YT max tag count
            "categoryId":  CATEGORY_MUSIC,
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
        "status": {
            "privacyStatus":           PRIVACY_STATUS,
            "selfDeclaredMadeForKids": False,
            "madeForKids":             False,
        },
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,   # 10 MB chunks
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    video_id = _resumable_upload(request)
    log.info(f"  ✓ Video uploaded! ID: {video_id}")

    # ── Set thumbnail ────────────────────────────────────────────────
    log.info("  Setting custom thumbnail...")
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg"),
        ).execute()
        log.info("  ✓ Thumbnail set!")
    except HttpError as e:
        log.warning(f"  ⚠️  Thumbnail upload failed: {e} (continuing)")

    return f"https://www.youtube.com/watch?v={video_id}"


def _resumable_upload(request) -> str:
    """
    Execute a resumable upload with exponential backoff retry.
    Returns the uploaded video ID.
    """
    response   = None
    error      = None
    retry      = 0
    max_retry  = 10
    retry_codes = [500, 502, 503, 504]

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                log.info(f"  ↑ Upload progress: {pct}%")
        except HttpError as e:
            if e.resp.status in retry_codes:
                error = f"HTTP {e.resp.status}: {e.content}"
            else:
                raise
        except Exception as e:
            error = str(e)

        if error:
            retry += 1
            if retry > max_retry:
                raise RuntimeError(f"Upload failed after {max_retry} retries: {error}")
            wait = 2 ** retry
            log.warning(f"  ⚠️  Upload error ({error}). Retrying in {wait}s...")
            time.sleep(wait)
            error = None

    return response["id"]
