"""
upload_youtube.py
Uploads video to YouTube and auto-organizes into language-specific playlists.
"""

import os
import json
import time
import logging
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

CATEGORY_MUSIC = "10"
PRIVACY_STATUS = os.environ.get("VIDEO_PRIVACY", "public")

# Playlist cache file
PLAYLIST_CACHE = Path("output/playlists.json")

# Playlist titles by language
PLAYLIST_TITLES = {
    "english":  "Slowed + Reverb | English Hits",
    "hindi":    "Slowed + Reverb | Hindi Songs",
    "punjabi":  "Slowed + Reverb | Punjabi Tracks",
    "haryanvi": "Slowed + Reverb | Haryanvi Music",
}


def _get_credentials() -> Credentials:
    """Load OAuth credentials from environment variables."""
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

    creds.refresh(Request())
    return creds


def _load_playlist_cache() -> dict:
    """Load cached playlist IDs."""
    if PLAYLIST_CACHE.exists():
        try:
            with open(PLAYLIST_CACHE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_playlist_cache(cache: dict):
    """Save playlist IDs to cache."""
    PLAYLIST_CACHE.parent.mkdir(exist_ok=True)
    with open(PLAYLIST_CACHE, "w") as f:
        json.dump(cache, f)


def _get_or_create_playlist(youtube, language: str) -> str:
    """
    Get existing playlist ID for language, or create if doesn't exist.
    Returns playlist ID.
    """
    cache = _load_playlist_cache()

    if language in cache:
        # Verify playlist still exists
        try:
            youtube.playlists().list(
                part="snippet",
                id=cache[language]
            ).execute()
            log.info(f"  Using existing {language} playlist: {cache[language]}")
            return cache[language]
        except HttpError:
            log.warning(f"  Cached playlist {cache[language]} not found, creating new...")

    # Create new playlist
    title = PLAYLIST_TITLES.get(language, f"Slowed + Reverb | {language.title()}")
    description = f"All {language.title()} songs slowed to 80% with reverb. Perfect for studying, chilling, or late-night drives. New uploads daily!"

    try:
        response = youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                },
                "status": {
                    "privacyStatus": "public"
                }
            }
        ).execute()

        playlist_id = response["id"]
        log.info(f"  ✓ Created new {language} playlist: {playlist_id}")

        # Cache it
        cache[language] = playlist_id
        _save_playlist_cache(cache)

        return playlist_id

    except HttpError as e:
        log.warning(f"  Failed to create playlist: {e}")
        return None


def _add_to_playlist(youtube, video_id: str, playlist_id: str):
    """Add video to playlist."""
    if not playlist_id:
        return

    try:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }
        ).execute()
        log.info(f"  ✓ Added to playlist: {playlist_id}")
    except HttpError as e:
        log.warning(f"  Failed to add to playlist: {e}")


def upload_to_youtube(
    video_path: str,
    thumbnail_path: str,
    title: str,
    description: str,
    tags: list[str],
    language: str = "english",
) -> str:
    """
    Uploads video, sets thumbnail, and adds to language playlist.
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
            "tags":        tags,
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
        chunksize=10 * 1024 * 1024,
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
        log.warning(f"  ⚠️  Thumbnail upload failed: {e}")

    # ── Add to playlist ──────────────────────────────────────────────
    log.info(f"  Adding to {language} playlist...")
    playlist_id = _get_or_create_playlist(youtube, language)
    _add_to_playlist(youtube, video_id, playlist_id)

    return f"https://www.youtube.com/watch?v={video_id}"


def _resumable_upload(request) -> str:
    """Execute resumable upload with retry."""
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
