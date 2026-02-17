"""
process_audio.py - Downloads video with yt-dlp, extracts audio with ffmpeg.
This is more reliable than yt-dlp's built-in audio extraction (-x).
"""

import os
import logging
import subprocess
from pathlib import Path

import numpy as np
from pydub import AudioSegment
from pedalboard import Pedalboard, Reverb, LowShelfFilter, HighShelfFilter, Compressor
import soundfile as sf
import librosa

log = logging.getLogger("yt-uploader")

SLOW_FACTOR  = 0.80
REVERB_ROOM  = 0.75
REVERB_WET   = 0.35
TARGET_LUFS  = -14.0
COOKIES_PATH = Path("/tmp/yt_cookies.txt")


class DownloadError(Exception):
    pass


def _write_cookies():
    """Write cookies from env var using Python (safe for multiline content)."""
    yt_cookies = os.environ.get("YT_COOKIES", "").strip()
    if not yt_cookies:
        log.warning("  YT_COOKIES env var is empty")
        return False
    COOKIES_PATH.write_text(yt_cookies, encoding="utf-8")
    size = COOKIES_PATH.stat().st_size
    log.info(f"  Cookies written: {size} bytes")
    return size > 200


def _try_download(url: str, out_video: Path, cookies_arg: list) -> bool:
    """
    Download the VIDEO file (not audio-only).
    Avoids all -x / --audio-format / -f conflicts entirely.
    ffmpeg extracts audio afterward.
    """
    clients = ["ios", "web", "android", "tv_embedded", "mweb"]

    for client in clients:
        log.info(f"  Trying client={client}...")
        cmd = [
            "yt-dlp",
            url,
            # Download best video+audio merged, or best single file
            "-f", "best[ext=mp4]/best",
            "-o", str(out_video),
            "--no-playlist",
            "--quiet",
            "--no-warnings",
            "--geo-bypass",
            "--merge-output-format", "mp4",
            "--extractor-args", f"youtube:player_client={client}",
            "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ] + cookies_arg

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and out_video.exists() and out_video.stat().st_size > 10000:
            log.info(f"  ✓ Download succeeded with client={client}")
            return True

        # Clean up partial file
        if out_video.exists():
            out_video.unlink()

        err = result.stderr[:120].strip()
        log.warning(f"  client={client} failed: {err}")

    return False


def process_audio(video_id: str, title: str, artist: str, temp_dir: str) -> str:
    temp      = Path(temp_dir)
    video_out = temp / f"{video_id}.mp4"
    mp3_raw   = temp / f"{video_id}_raw.mp3"
    out       = temp / f"{video_id}_slowed_reverb.mp3"

    # Write cookies fresh for each attempt
    has_cookies = _write_cookies()
    cookies_arg = ["--cookies", str(COOKIES_PATH)] if has_cookies else []

    # Download video
    log.info(f"  Downloading video_id={video_id}...")
    success = _try_download(
        f"https://www.youtube.com/watch?v={video_id}",
        video_out,
        cookies_arg,
    )

    if not success:
        raise DownloadError(f"All clients failed for {video_id}")

    log.info(f"  Video downloaded: {video_out.stat().st_size / (1024*1024):.1f} MB")

    # Extract audio with ffmpeg (very reliable, no yt-dlp format issues)
    log.info("  Extracting audio with ffmpeg...")
    result = subprocess.run([
        "ffmpeg", "-i", str(video_out),
        "-vn",                    # no video
        "-acodec", "libmp3lame",
        "-ar", "44100",
        "-ac", "2",
        "-b:a", "320k",
        str(mp3_raw),
        "-y", "-loglevel", "error"
    ], capture_output=True, text=True)

    if result.returncode != 0:
        raise DownloadError(f"ffmpeg audio extraction failed: {result.stderr}")

    # Clean up video file to save space
    video_out.unlink()
    log.info(f"  MP3 extracted: {mp3_raw.stat().st_size / 1024:.0f} KB")

    # Slow down
    log.info("  Applying slowed effect (0.80x)...")
    y, sr = librosa.load(str(mp3_raw), sr=44100, mono=False)

    if y.ndim == 1:
        y_slow = librosa.effects.time_stretch(y, rate=SLOW_FACTOR)
        y_slow = np.stack([y_slow, y_slow])
    else:
        left  = librosa.effects.time_stretch(y[0], rate=SLOW_FACTOR)
        right = librosa.effects.time_stretch(y[1], rate=SLOW_FACTOR)
        y_slow = np.stack([left, right])

    # Effects chain
    log.info("  Applying reverb, EQ, compression...")
    board = Pedalboard([
        Compressor(threshold_db=-18, ratio=3.0, attack_ms=5.0, release_ms=100.0),
        LowShelfFilter(cutoff_frequency_hz=200, gain_db=3.0),
        HighShelfFilter(cutoff_frequency_hz=8000, gain_db=-2.5),
        Reverb(
            room_size=REVERB_ROOM, damping=0.6,
            wet_level=REVERB_WET, dry_level=1.0 - REVERB_WET,
            width=0.9, freeze_mode=0.0,
        ),
    ])

    y_effected = board(y_slow.astype(np.float32), sr)
    y_effected = _normalize_loudness(y_effected, sr)

    wav_path = temp / f"{video_id}_processed.wav"
    sf.write(str(wav_path), y_effected.T, sr, subtype="PCM_24")

    log.info("  Adding fade-in/out...")
    seg = AudioSegment.from_wav(str(wav_path))
    seg = seg.fade_in(3000).fade_out(4000)
    seg.export(str(out), format="mp3", bitrate="320k",
               tags={"title": f"{title} (Slowed + Reverb)", "artist": artist})

    log.info(f"  ✓ Done: {out.name} ({out.stat().st_size / (1024*1024):.1f} MB)")
    return str(out)


def _normalize_loudness(audio: np.ndarray, sr: int) -> np.ndarray:
    try:
        import pyloudnorm as pyln
        meter    = pyln.Meter(sr)
        loudness = meter.integrated_loudness(audio.T)
        if loudness > -70:
            audio = pyln.normalize.loudness(audio.T, loudness, TARGET_LUFS).T
    except ImportError:
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio / peak * 0.9
    return audio
