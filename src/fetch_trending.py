"""
fetch_trending.py
Fetches the most viral/trending music from YouTube using the Data API v3.
Avoids re-uploading songs that were already processed.
"""

import os
import json
import random
import logging
from pathlib import Path
from googleapiclient.discovery import build

log = logging.getLogger("yt-uploader")

# Track uploaded songs so we never repeat
UPLOADED_LOG = Path("output/uploaded.json")

# Trending music search queries — rotates each run for variety
SEARCH_QUERIES = [
    "trending songs 2025",
    "top hits 2025 official audio",
    "viral songs this week 2025",
    "new music 2025 popular",
    "best songs 2025 trending",
    "most streamed songs 2025",
    "viral hindi songs 2025",
    "viral english songs 2025",
]


def _load_uploaded() -> set:
    if UPLOADED_LOG.exists():
        with open(UPLOADED_LOG) as f:
            return set(json.load(f))
    return set()


def _save_uploaded(video_ids: set):
    UPLOADED_LOG.parent.mkdir(exist_ok=True)
    with open(UPLOADED_LOG, "w") as f:
        json.dump(list(video_ids), f)


def get_trending_song() -> dict | None:
    """
    Returns a dict: {video_id, title, artist, duration_seconds, view_count}
    Picks a trending track not already uploaded.
    Falls back to YouTube chart if search quota is low.
    """
    api_key = os.environ["YOUTUBE_API_KEY"]
    youtube = build("youtube", "v3", developerKey=api_key)
    uploaded = _load_uploaded()

    query = random.choice(SEARCH_QUERIES)
    log.info(f"Searching: '{query}'")

    # First try: Most Popular Music chart
    try:
        chart_resp = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            chart="mostPopular",
            videoCategoryId="10",   # Music category
            regionCode="US",
            maxResults=25,
        ).execute()

        for item in chart_resp.get("items", []):
            vid_id = item["id"]
            if vid_id in uploaded:
                continue

            snippet = item["snippet"]
            title   = snippet.get("title", "Unknown")
            channel = snippet.get("channelTitle", "Unknown Artist")

            # Skip if video is too long (>8 min) or too short (<1 min)
            duration = item["contentDetails"].get("duration", "PT0S")
            secs = _parse_duration(duration)
            if not (60 <= secs <= 480):
                continue

            # Record as uploaded
            uploaded.add(vid_id)
            _save_uploaded(uploaded)

            return {
                "video_id": vid_id,
                "title":    _clean_title(title),
                "artist":   _clean_artist(channel),
                "duration": secs,
                "view_count": int(item["statistics"].get("viewCount", 0)),
            }

    except Exception as e:
        log.warning(f"Chart lookup failed ({e}), falling back to search...")

    # Fallback: search query
    search_resp = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        videoCategoryId="10",
        order="viewCount",
        maxResults=15,
        videoDuration="medium",
    ).execute()

    for item in search_resp.get("items", []):
        vid_id = item["id"]["videoId"]
        if vid_id in uploaded:
            continue

        snippet = item["snippet"]
        title   = snippet.get("title", "Unknown")
        channel = snippet.get("channelTitle", "Unknown Artist")

        uploaded.add(vid_id)
        _save_uploaded(uploaded)

        return {
            "video_id": vid_id,
            "title":    _clean_title(title),
            "artist":   _clean_artist(channel),
            "duration": 180,   # estimate
            "view_count": 0,
        }

    log.error("No new trending songs found!")
    return None


def _parse_duration(iso: str) -> int:
    """Parse ISO 8601 duration (PT4M13S) → seconds."""
    import re
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not match:
        return 0
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = int(match.group(3) or 0)
    return h * 3600 + m * 60 + s


def _clean_title(title: str) -> str:
    """Remove common YouTube title noise."""
    import re
    noise = [
        r"\(Official\s*(Music\s*)?Video\)",
        r"\(Official\s*Audio\)",
        r"\(Lyric\s*Video\)",
        r"\[Official.*?\]",
        r"\(HD\)",
        r"\(4K\)",
        r"ft\..*",
        r"feat\..*",
    ]
    for n in noise:
        title = re.sub(n, "", title, flags=re.IGNORECASE)
    return title.strip(" -|")


def _clean_artist(channel: str) -> str:
    """Remove 'VEVO', 'Official' etc from channel names."""
    import re
    return re.sub(r"(VEVO|Official|Music|Channel)", "", channel, flags=re.IGNORECASE).strip()
