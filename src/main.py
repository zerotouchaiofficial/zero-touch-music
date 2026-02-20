"""
main.py - Handles regular songs and mashups with copyright detection
Pattern: 4 regular songs + 1 mashup per day
"""

import os
import sys
import logging
import traceback
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from fetch_trending import get_trending_songs, mark_uploaded
from process_audio import process_audio, DownloadError
from create_video import create_video
from generate_thumbnail import generate_thumbnail
from upload_youtube import upload_to_youtube, QuotaExceededError, get_youtube_service
from check_copyright import check_video_status, delete_video
from create_mashup import create_mashup
from seo_generator import generate_seo_metadata
from utils import cleanup_temp_files, setup_logging, send_discord_notification

CHANNEL_NAME = os.environ.get("CHANNEL_NAME", "LoFi Aura")
OUTPUT_DIR   = Path("output")
TEMP_DIR     = Path("temp")
UPLOAD_TYPE_FILE = OUTPUT_DIR / "upload_type.txt"

OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)


def get_next_upload_type() -> str:
    """
    Returns next upload type in rotation: regular, regular, regular, regular, mashup
    """
    if UPLOAD_TYPE_FILE.exists():
        content = UPLOAD_TYPE_FILE.read_text().strip()
        count = int(content) if content.isdigit() else 0
    else:
        count = 0
    
    # Pattern: 0,1,2,3 = regular, 4 = mashup, then reset
    upload_type = "mashup" if count == 4 else "regular"
    
    # Update counter
    next_count = (count + 1) % 5
    UPLOAD_TYPE_FILE.write_text(str(next_count))
    
    return upload_type


def try_upload_with_retry(song, processed_audio, language, max_retries=3):
    """
    Uploads video and checks if blocked. Retries with different song if blocked.
    Returns (success: bool, video_url: str or None)
    """
    log = logging.getLogger("yt-uploader")
    youtube = get_youtube_service()
    
    for attempt in range(max_retries):
        try:
            log.info("\n📝 Generating SEO...")
            metadata = generate_seo_metadata(
                song_title=song["title"],
                artist=song["artist"],
                channel_name=CHANNEL_NAME,
                original_url=f"https://www.youtube.com/watch?v={song['video_id']}",
            )

            log.info("\n🎬 Creating video...")
            video_path = create_video(
                audio_path=processed_audio,
                song_title=song["title"],
                artist=song["artist"],
                channel_name=CHANNEL_NAME,
                output_dir=str(OUTPUT_DIR),
                temp_dir=str(TEMP_DIR),
            )

            log.info("\n🖼️  Creating thumbnail...")
            thumbnail_path = generate_thumbnail(
                song_title=song["title"],
                artist=song["artist"],
                channel_name=CHANNEL_NAME,
                output_dir=str(OUTPUT_DIR),
            )

            log.info("\n🚀 Uploading to YouTube...")
            video_url = upload_to_youtube(
                video_path=video_path,
                thumbnail_path=thumbnail_path,
                title=metadata["title"],
                description=metadata["description"],
                tags=metadata["tags"],
                language=language,
            )
            
            video_id = video_url.split("=")[-1]
            log.info(f"✅ Uploaded! → {video_url}")
            
            # Check if blocked
            log.info("\n🔍 Checking copyright status...")
            status = check_video_status(youtube, video_id)
            
            if status["blocked"]:
                log.warning(f"❌ Video blocked: {status['status']}")
                log.warning("  Deleting and retrying with different song...")
                delete_video(youtube, video_id)
                return False, None
            
            if status["restricted"]:
                log.warning(f"⚠️  Video restricted: {status['status']}")
                log.info("  Keeping video (partial availability better than none)")
            else:
                log.info(f"✅ Video status: {status['status']}")
            
            return True, video_url
            
        except Exception as e:
            log.error(f"❌ Upload attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                log.info("  Retrying...")
                cleanup_temp_files(str(TEMP_DIR))
            else:
                raise
    
    return False, None


def create_regular_upload():
    """Creates and uploads a regular slowed+reverb song."""
    log = logging.getLogger("yt-uploader")
    
    log.info("📡 Fetching trending songs for regular upload...")
    candidates, language = get_trending_songs(max_candidates=15)
    
    if not candidates:
        log.error("No songs found")
        return False
    
    # Try songs until one uploads successfully
    for i, candidate in enumerate(candidates):
        log.info(f"\n🎵 Song {i+1}/{len(candidates)}: '{candidate['title']}' by {candidate['artist']}")
        
        try:
            log.info("🎧 Processing audio...")
            processed_audio = process_audio(
                video_id=candidate["video_id"],
                title=candidate["title"],
                artist=candidate["artist"],
                temp_dir=str(TEMP_DIR),
            )
            
            success, video_url = try_upload_with_retry(candidate, processed_audio, language)
            
            if success:
                mark_uploaded(
                    video_id=candidate["video_id"],
                    title=candidate["title"],
                    artist=candidate["artist"],
                    youtube_url=video_url,
                    language=language,
                )
                
                send_discord_notification(
                    title=f"✅ Regular Upload ({language.upper()})",
                    description=f"**{candidate['title']}** by {candidate['artist']}\n[Watch]({video_url})",
                    color=5763719
                )
                
                cleanup_temp_files(str(TEMP_DIR))
                return True
            else:
                log.warning("  Video was blocked, trying next song...")
                continue
                
        except (DownloadError, Exception) as e:
            log.warning(f"⏭️  Failed: {e}")
            cleanup_temp_files(str(TEMP_DIR))
            continue
    
    log.error("❌ All songs failed")
    return False


def create_mashup_upload():
    """Creates and uploads a mashup of 2 songs."""
    log = logging.getLogger("yt-uploader")
    
    log.info("📡 Fetching 2 trending songs for mashup...")
    candidates, language = get_trending_songs(max_candidates=20)
    
    if len(candidates) < 2:
        log.error("Not enough songs for mashup")
        return False
    
    # Try pairs of songs
    for i in range(len(candidates) - 1):
        song1 = candidates[i]
        song2 = candidates[i + 1]
        
        log.info(f"\n🎵 Mashup attempt: '{song1['title']}' x '{song2['title']}'")
        
        try:
            # Process both songs
            log.info("🎧 Processing song 1...")
            audio1 = process_audio(
                video_id=song1["video_id"],
                title=song1["title"],
                artist=song1["artist"],
                temp_dir=str(TEMP_DIR),
            )
            
            log.info("🎧 Processing song 2...")
            audio2 = process_audio(
                video_id=song2["video_id"],
                title=song2["title"],
                artist=song2["artist"],
                temp_dir=str(TEMP_DIR),
            )
            
            # Create mashup
            log.info("🎛️  Creating mashup...")
            mashup_audio = create_mashup(
                audio1, audio2, str(TEMP_DIR),
                song1["title"], song2["title"]
            )
            
            # Create combined metadata
            mashup_song = {
                "video_id": f"{song1['video_id']}_x_{song2['video_id']}",
                "title": f"{song1['title']} x {song2['title']}",
                "artist": f"{song1['artist']} x {song2['artist']}",
            }
            
            success, video_url = try_upload_with_retry(mashup_song, mashup_audio, language)
            
            if success:
                # Mark both songs as used
                mark_uploaded(song1["video_id"], song1["title"], song1["artist"], video_url, language)
                mark_uploaded(song2["video_id"], song2["title"], song2["artist"], video_url, language)
                
                send_discord_notification(
                    title=f"✅ Mashup Upload ({language.upper()})",
                    description=f"**{mashup_song['title']}**\n[Watch]({video_url})",
                    color=9055202  # purple
                )
                
                cleanup_temp_files(str(TEMP_DIR))
                return True
            else:
                log.warning("  Mashup was blocked, trying next pair...")
                cleanup_temp_files(str(TEMP_DIR))
                continue
                
        except (DownloadError, Exception) as e:
            log.warning(f"⏭️  Mashup failed: {e}")
            cleanup_temp_files(str(TEMP_DIR))
            continue
    
    log.error("❌ All mashup attempts failed")
    return False


def run_pipeline():
    log = setup_logging()
    log.info("=" * 60)
    log.info(f"🎵 YT Auto-Uploader started at {datetime.utcnow().isoformat()}")
    log.info("=" * 60)
    
    upload_type = get_next_upload_type()
    log.info(f"📋 Upload type: {upload_type.upper()}")
    
    try:
        if upload_type == "mashup":
            success = create_mashup_upload()
        else:
            success = create_regular_upload()
        
        if success:
            log.info("\n🎉 Upload complete!")
        else:
            log.error("\n❌ Upload failed")
            sys.exit(1)
            
    except QuotaExceededError:
        log.warning("⏸️  YouTube quota exceeded for today!")
        send_discord_notification(
            title="⏸️  Daily Quota Reached",
            description="Will resume tomorrow.",
            color=16776960
        )
        sys.exit(0)
        
    except Exception as e:
        log.error(f"❌ Pipeline error: {e}")
        log.error(traceback.format_exc())
        send_discord_notification(
            title="❌ Pipeline Error",
            description=str(e)[:200],
            color=15158332
        )
        sys.exit(1)


if __name__ == "__main__":
    run_pipeline()
