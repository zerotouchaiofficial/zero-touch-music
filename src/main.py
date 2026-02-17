"""
Main orchestrator for the YouTube Auto-Uploader.
Fetches trending songs, processes audio (slowed+reverb),
creates video with thumbnail, and uploads to YouTube.
"""

import os
import sys
import logging
import traceback
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from fetch_trending import get_trending_song
from process_audio import process_audio
from create_video import create_video
from generate_thumbnail import generate_thumbnail
from upload_youtube import upload_to_youtube
from seo_generator import generate_seo_metadata
from utils import cleanup_temp_files, setup_logging

# ─── Config ────────────────────────────────────────────────────────────────────
CHANNEL_NAME = os.environ.get("CHANNEL_NAME", "LoFi Aura")
OUTPUT_DIR   = Path("output")
TEMP_DIR     = Path("temp")

OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)


def run_pipeline():
    log = setup_logging()
    log.info("=" * 60)
    log.info(f"🎵 YT Auto-Uploader started at {datetime.utcnow().isoformat()}")
    log.info("=" * 60)

    try:
        # ── Step 1: Fetch trending song ──────────────────────────────
        log.info("📡 Step 1: Fetching trending song...")
        song = get_trending_song()
        if not song:
            log.error("No trending song found. Exiting.")
            sys.exit(1)

        log.info(f"✅ Found: '{song['title']}' by {song['artist']}")

        # ── Step 2: Process audio (slowed + reverb) ──────────────────
        log.info("🎧 Step 2: Processing audio (slowed+reverb)...")
        processed_audio = process_audio(
            video_id=song["video_id"],
            title=song["title"],
            artist=song["artist"],
            temp_dir=str(TEMP_DIR),
        )
        log.info(f"✅ Audio processed: {processed_audio}")

        # ── Step 3: Generate SEO metadata ────────────────────────────
        log.info("📝 Step 3: Generating SEO metadata...")
        metadata = generate_seo_metadata(
            song_title=song["title"],
            artist=song["artist"],
            channel_name=CHANNEL_NAME,
            original_url=f"https://www.youtube.com/watch?v={song['video_id']}",
        )
        log.info(f"✅ Title: {metadata['title']}")

        # ── Step 4: Create video ─────────────────────────────────────
        log.info("🎬 Step 4: Creating video...")
        video_path = create_video(
            audio_path=processed_audio,
            song_title=song["title"],
            artist=song["artist"],
            channel_name=CHANNEL_NAME,
            output_dir=str(OUTPUT_DIR),
            temp_dir=str(TEMP_DIR),
        )
        log.info(f"✅ Video created: {video_path}")

        # ── Step 5: Generate thumbnail ───────────────────────────────
        log.info("🖼️  Step 5: Generating thumbnail...")
        thumbnail_path = generate_thumbnail(
            song_title=song["title"],
            artist=song["artist"],
            channel_name=CHANNEL_NAME,
            output_dir=str(OUTPUT_DIR),
        )
        log.info(f"✅ Thumbnail: {thumbnail_path}")

        # ── Step 6: Upload to YouTube ────────────────────────────────
        log.info("🚀 Step 6: Uploading to YouTube...")
        video_url = upload_to_youtube(
            video_path=video_path,
            thumbnail_path=thumbnail_path,
            title=metadata["title"],
            description=metadata["description"],
            tags=metadata["tags"],
        )
        log.info(f"✅ Uploaded! → {video_url}")

        # ── Step 7: Cleanup ──────────────────────────────────────────
        log.info("🧹 Step 7: Cleaning up temp files...")
        cleanup_temp_files(str(TEMP_DIR))

        log.info("🎉 Pipeline complete!")
        return True

    except Exception as e:
        log.error(f"❌ Pipeline failed: {e}")
        log.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    run_pipeline()
