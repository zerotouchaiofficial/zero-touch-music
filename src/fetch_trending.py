"""
fetch_trending.py - Returns a list of candidate songs to try (not just one).
"""

import os
import json
import random
import logging
from pathlib import Path
from googleapiclient.discovery import build

log = logging.getLogger("yt-uploader")
UPLOADED_LOG = Path("output/uploaded.json")
BLOCKLIST = {"c5aYTMnACfk", "1FVF-9KQiPo"}

SEARCH_QUERIES = [
    "trending songs 2025",
    "top hits 2025 official audio",
    "viral songs this week 2025",
    "new music 2025 popular",
    "best songs 2025 trending",
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


def get_trending_songs(max_candidates: int = 10) -> list:
    """
    Returns a list of up to max_candidates song dicts to try.
    Caller should iterate and use the first one that downloads successfully.
    """
    api_key = os.environ["YOUTUBE_API_KEY"]
    youtube = build("youtube", "v3", developerKey=api_key)
    uploaded = _load_uploaded()
    skip = uploaded | BLOCKLIST
    candidates = []

    # Try chart first
    try:
        resp = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            chart="mostPopular",
            videoCategoryId="10",
            regionCode="US",
            maxResults=50,
        ).execute()

        for item in resp.get("items", []):
            vid_id = item["id"]
            if vid_id in skip:
                continue
            secs = _parse_duration(item["contentDetails"].get("duration", "PT0S"))
            if not (60 <= secs <= 480):
                continue
            snippet = item["snippet"]
            candidates.append({
                "video_id":   vid_id,
                "title":      _clean_title(snippet.get("title", "Unknown")),
                "artist":     _clean_artist(snippet.get("channelTitle", "Unknown")),
                "duration":   secs,
            })
            if len(candidates) >= max_candidates:
                break

    except Exception as e:
        log.warning(f"Chart lookup failed: {e}")

    # Fill remaining from search if needed
    if len(candidates) < max_candidates:
        try:
            query = random.choice(SEARCH_QUERIES)
            resp = youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                videoCategoryId="10",
                order="viewCount",
                maxResults=25,
                videoDuration="medium",
            ).execute()

            for item in resp.get("items", []):
                vid_id = item["id"]["videoId"]
                if vid_id in skip:
                    continue
                snippet = item["snippet"]
                candidates.append({
                    "video_id":   vid_id,
                    "title":      _clean_title(snippet.get("title", "Unknown")),
                    "artist":     _clean_artist(snippet.get("channelTitle", "Unknown")),
                    "duration":   180,
                })
                if len(candidates) >= max_candidates:
                    break
        except Exception as e:
            log.warning(f"Search fallback failed: {e}")

    log.info(f"  Found {len(candidates)} candidate songs to try")
    return candidates


def mark_uploaded(video_id: str):
    """Call this only after a successful upload."""
    uploaded = _load_uploaded()
    uploaded.add(video_id)
    _save_uploaded(uploaded)


def _parse_duration(iso: str) -> int:
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        return 0
    return int(m.group(1) or 0)*3600 + int(m.group(2) or 0)*60 + int(m.group(3) or 0)


def _clean_title(t: str) -> str:
    import re
    for p in [r"\(Official.*?\)", r"\[Official.*?\]", r"\(HD\)", r"\(4K\)", r"ft\..*", r"feat\..*", r"\(Lyric.*?\)"]:
        t = re.sub(p, "", t, flags=re.IGNORECASE)
    return t.strip(" -|")


def _clean_artist(c: str) -> str:
    import re
    return re.sub(r"(VEVO|Official|Music|Channel)", "", c, flags=re.IGNORECASE).strip()
