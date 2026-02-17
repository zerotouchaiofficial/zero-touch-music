"""
create_video.py
Creates a beautiful, animated lofi-aesthetic video:
  • Deep gradient background (purple/blue/teal)
  • Slowly rotating and pulsing geometric patterns
  • Particle effect (floating dots)
  • Centered text: CHANNEL NAME | SONG TITLE | Slowed + Reverb
  • Subtle vignette and noise grain overlay for cinema feel
  • 1920×1080 @ 24fps — YouTube recommended
"""

import os
import logging
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip,
    VideoClip, concatenate_videoclips
)
from moviepy.video.fx.all import fadein, fadeout
import colorsys
import math

log = logging.getLogger("yt-uploader")

WIDTH, HEIGHT = 1920, 1080
FPS          = 24


# ─── Colour Palettes ────────────────────────────────────────────────────────────
PALETTES = [
    # Purple Dream
    [(25, 10, 60), (70, 20, 120), (120, 40, 160), (180, 80, 200)],
    # Ocean Night
    [(5, 20, 60), (10, 60, 120), (20, 100, 160), (30, 140, 190)],
    # Sunset Lofi
    [(40, 10, 40), (100, 20, 60), (160, 50, 80), (200, 100, 80)],
    # Forest Night
    [(5, 30, 20), (10, 70, 50), (20, 100, 70), (40, 130, 90)],
]


def create_video(audio_path: str, song_title: str, artist: str,
                 channel_name: str, output_dir: str, temp_dir: str) -> str:
    """
    Creates the final video file.
    Returns path to the output .mp4 file.
    """
    import random
    palette = random.choice(PALETTES)

    audio      = AudioFileClip(audio_path)
    duration   = audio.duration
    out_path   = Path(output_dir) / f"{_safe_filename(song_title)}_lofi.mp4"

    log.info(f"  Duration: {duration:.1f}s | Palette: {palette[0]}")
    log.info("  Rendering animated background frames...")

    def make_frame(t: float) -> np.ndarray:
        return _render_frame(t, duration, palette, channel_name, song_title, artist)

    video_clip = VideoClip(make_frame, duration=duration).set_fps(FPS)
    video_clip = video_clip.set_audio(audio)
    video_clip = fadein(video_clip, 2).fadeout(3)

    log.info("  Writing video file (this may take a few minutes)...")
    video_clip.write_videofile(
        str(out_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate="6000k",
        audio_bitrate="320k",
        preset="medium",
        ffmpeg_params=["-profile:v", "high", "-level", "4.0"],
        threads=4,
        logger=None,
    )

    log.info(f"  ✓ Video: {out_path.name} ({out_path.stat().st_size / (1024*1024):.1f} MB)")
    return str(out_path)


def _render_frame(t: float, duration: float, palette: list,
                  channel_name: str, song_title: str, artist: str) -> np.ndarray:
    """Render a single frame at time t."""
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)

    # ── Animated gradient background ─────────────────────────────────
    _draw_gradient(img, draw, t, palette)

    # ── Floating particles ───────────────────────────────────────────
    _draw_particles(draw, t, palette)

    # ── Rotating geometric rings ─────────────────────────────────────
    _draw_rings(draw, t, palette)

    # ── Vignette ─────────────────────────────────────────────────────
    img = _apply_vignette(img)

    # ── Text overlay ─────────────────────────────────────────────────
    _draw_text_overlay(draw if False else ImageDraw.Draw(img),
                       img, t, duration, channel_name, song_title, artist)

    # ── Film grain ───────────────────────────────────────────────────
    img = _add_grain(img, intensity=8)

    return np.array(img)


# ─── Visual helpers ─────────────────────────────────────────────────────────────

def _draw_gradient(img, draw, t, palette):
    """Animated diagonal gradient that slowly shifts."""
    shift = (math.sin(t * 0.1) + 1) / 2  # 0–1 oscillating
    c1 = _lerp_color(palette[0], palette[1], shift)
    c2 = _lerp_color(palette[2], palette[3], 1 - shift)

    for y in range(HEIGHT):
        factor = y / HEIGHT
        r = int(c1[0] + (c2[0] - c1[0]) * factor)
        g = int(c1[1] + (c2[1] - c1[1]) * factor)
        b = int(c1[2] + (c2[2] - c1[2]) * factor)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))


def _draw_particles(draw, t, palette):
    """Floating glowing dots that drift upward."""
    import random
    rng = random.Random(42)  # deterministic seed so particles stay consistent
    for i in range(60):
        seed_x = rng.random()
        seed_y = rng.random()
        speed  = 0.02 + rng.random() * 0.05
        size   = 2 + rng.random() * 6

        x = seed_x * WIDTH
        y = (seed_y * HEIGHT - t * speed * HEIGHT * 0.3) % HEIGHT
        alpha = int(80 + 120 * abs(math.sin(t * 0.5 + i)))

        color_base = palette[rng.randint(1, len(palette) - 1)]
        color = tuple(min(255, c + 100) for c in color_base) + (alpha,)

        # Soft circle (fake glow with multiple circles)
        for spread in [size * 2, size]:
            faded = tuple(min(255, c + 50) for c in color_base) + (alpha // 3,)
            draw.ellipse([x - spread, y - spread, x + spread, y + spread],
                         fill=faded)
        draw.ellipse([x - size/2, y - size/2, x + size/2, y + size/2],
                     fill=tuple(min(255, c + 150) for c in color_base))


def _draw_rings(draw, t, palette):
    """Slowly rotating concentric ellipses."""
    cx, cy = WIDTH // 2, HEIGHT // 2
    angle  = t * 3  # degrees per second
    for i in range(5):
        r_x = 300 + i * 80
        r_y = 200 + i * 50
        opacity = max(0, 60 - i * 10)
        color = palette[i % len(palette)] + (opacity,)

        # Rotate by drawing an arc approximation
        rot = math.radians(angle + i * 20)
        cos_r, sin_r = math.cos(rot), math.sin(rot)
        pts = []
        for deg in range(0, 361, 5):
            rad = math.radians(deg)
            ex = r_x * math.cos(rad)
            ey = r_y * math.sin(rad)
            rx = cx + ex * cos_r - ey * sin_r
            ry = cy + ex * sin_r + ey * cos_r
            pts.append((rx, ry))

        if len(pts) > 1:
            try:
                draw.line(pts, fill=palette[i % len(palette)] + (opacity,), width=2)
            except Exception:
                pass


def _apply_vignette(img: Image.Image) -> Image.Image:
    """Dark vignette around edges."""
    vignette = Image.new("L", (WIDTH, HEIGHT), 0)
    v_draw   = ImageDraw.Draw(vignette)
    steps    = 50
    for i in range(steps):
        factor = i / steps
        gray   = int(255 * factor)
        margin = int((1 - factor) * min(WIDTH, HEIGHT) * 0.55)
        v_draw.rectangle([margin, margin, WIDTH - margin, HEIGHT - margin], fill=gray)

    vignette = vignette.filter(ImageFilter.GaussianBlur(80))
    black    = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    img      = Image.composite(img, black, vignette)
    return img


def _draw_text_overlay(draw, img, t, duration, channel_name, song_title, artist):
    """
    Central text block:
      [Channel Name]     ← small, stylized
      SONG TITLE         ← large bold
      artist             ← medium
      ✦ Slowed + Reverb ✦  ← small accent
    """
    try:
        # Try to load fonts (fall back to default if unavailable)
        font_xl  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        font_lg  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
        font_md  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        font_sm  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except Exception:
        font_xl = font_lg = font_md = font_sm = ImageFont.load_default()

    # Pulse alpha effect (subtle breathing)
    alpha_pulse = int(220 + 35 * math.sin(t * 0.8))

    cx = WIDTH // 2
    line_gap = 20

    # Shadow helper
    def shadow_text(text, font, y, color=(255, 255, 255), opacity=None):
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
        except Exception:
            tw = len(text) * 20
        x = cx - tw // 2

        # Shadow
        draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0, 120))
        # Main text
        final_color = color + (opacity or alpha_pulse,)
        draw.text((x, y), text, font=font, fill=final_color)
        try:
            return draw.textbbox((0, 0), text, font=font)[3]  # height
        except Exception:
            return 60

    # ── Semi-transparent pill background ───────────────────────────────
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    box_w, box_h = 900, 400
    box_x = cx - box_w // 2
    box_y = HEIGHT // 2 - box_h // 2
    ov_draw.rounded_rectangle(
        [box_x, box_y, box_x + box_w, box_y + box_h],
        radius=30,
        fill=(0, 0, 0, 130),
    )
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"),
              (0, 0))

    # ── Render text lines ───────────────────────────────────────────────
    draw = ImageDraw.Draw(img)

    y_start = HEIGHT // 2 - 180

    # Channel name (smaller, accent color)
    shadow_text(f"♫  {channel_name}  ♫", font_md, y_start,
                color=(200, 170, 255), opacity=200)
    y_start += 50 + line_gap

    # Divider line
    draw.line([cx - 300, y_start, cx + 300, y_start], fill=(255, 255, 255, 80), width=1)
    y_start += 20

    # Song title (big and bold)
    # Wrap if title is long
    title_display = song_title if len(song_title) <= 32 else song_title[:30] + "…"
    shadow_text(title_display, font_xl, y_start, color=(255, 255, 255))
    y_start += 95 + line_gap

    # Artist
    shadow_text(artist, font_lg, y_start, color=(200, 230, 255), opacity=190)
    y_start += 60 + line_gap

    # Divider line
    draw.line([cx - 200, y_start, cx + 200, y_start], fill=(255, 255, 255, 60), width=1)
    y_start += 20

    # Slowed + Reverb badge
    shadow_text("✦  Slowed  +  Reverb  ✦", font_sm, y_start,
                color=(255, 200, 255), opacity=210)

    # Subtle progress bar at bottom
    progress = t / duration
    bar_y    = HEIGHT - 20
    bar_w    = int(WIDTH * progress)
    draw.rectangle([0, bar_y, WIDTH, HEIGHT], fill=(0, 0, 0, 120))
    draw.rectangle([0, bar_y + 4, bar_w, HEIGHT - 4], fill=(180, 100, 255, 200))


def _add_grain(img: Image.Image, intensity: int = 10) -> Image.Image:
    """Add subtle film grain / noise."""
    arr   = np.array(img).astype(np.int16)
    noise = np.random.randint(-intensity, intensity, arr.shape, dtype=np.int16)
    arr   = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def _lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _safe_filename(s: str) -> str:
    import re
    return re.sub(r"[^\w\-]", "_", s)[:40]
