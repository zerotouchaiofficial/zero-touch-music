"""
create_video.py
Creates animated lofi video with smart text wrapping.
"""

import logging
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import VideoClip, AudioFileClip
from moviepy.video.fx.all import fadein, fadeout
import math
import random
import re

log = logging.getLogger("yt-uploader")

WIDTH, HEIGHT = 1920, 1080
FPS           = 24

PALETTES = [
    [(25, 10, 60),  (70, 20, 120),  (120, 40, 160), (180, 80, 200)],
    [(5, 20, 60),   (10, 60, 120),  (20, 100, 160), (30, 140, 190)],
    [(40, 10, 40),  (100, 20, 60),  (160, 50, 80),  (200, 100, 80)],
    [(5, 30, 20),   (10, 70, 50),   (20, 100, 70),  (40, 130, 90)],
]


def create_video(audio_path: str, song_title: str, artist: str,
                 channel_name: str, output_dir: str, temp_dir: str) -> str:
    palette  = random.choice(PALETTES)
    audio    = AudioFileClip(audio_path)
    duration = audio.duration
    out_path = Path(output_dir) / f"{_safe(song_title)}_lofi.mp4"

    log.info(f"  Duration: {duration:.1f}s")

    def make_frame(t: float) -> np.ndarray:
        return _render_frame(t, duration, palette, channel_name, song_title, artist)

    video_clip = VideoClip(make_frame, duration=duration).set_fps(FPS)
    video_clip = video_clip.set_audio(audio)
    video_clip = fadein(video_clip, 2).fadeout(3)

    log.info("  Writing video file (this takes a few minutes)...")
    video_clip.write_videofile(
        str(out_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate="4000k",
        audio_bitrate="320k",
        preset="faster",
        threads=4,
        logger=None,
    )

    log.info(f"  ✓ Video: {out_path.name} ({out_path.stat().st_size / (1024*1024):.1f} MB)")
    return str(out_path)


def _render_frame(t, duration, palette, channel_name, song_title, artist):
    img  = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)

    _draw_gradient(draw, t, palette)
    _draw_particles(draw, t, palette)
    _draw_rings(draw, t, palette)
    img  = _apply_vignette(img)
    draw = ImageDraw.Draw(img)
    _draw_text_overlay(draw, img, t, duration, channel_name, song_title, artist)
    img  = _add_grain(img)

    return np.array(img)


def _draw_gradient(draw, t, palette):
    shift = (math.sin(t * 0.1) + 1) / 2
    c1 = _lerp(palette[0], palette[1], shift)
    c2 = _lerp(palette[2], palette[3], 1 - shift)
    for y in range(HEIGHT):
        f = y / HEIGHT
        r = int(c1[0] + (c2[0] - c1[0]) * f)
        g = int(c1[1] + (c2[1] - c1[1]) * f)
        b = int(c1[2] + (c2[2] - c1[2]) * f)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))


def _draw_particles(draw, t, palette):
    rng = random.Random(42)
    for i in range(60):
        sx, sy   = rng.random(), rng.random()
        speed    = 0.02 + rng.random() * 0.05
        size     = 2 + rng.random() * 6
        x        = sx * WIDTH
        y        = (sy * HEIGHT - t * speed * HEIGHT * 0.3) % HEIGHT
        cb       = palette[rng.randint(1, len(palette) - 1)]
        glow_col = tuple(min(255, c + 100) for c in cb)
        for spread in [size * 2, size]:
            draw.ellipse([x - spread, y - spread, x + spread, y + spread],
                         fill=tuple(min(255, c + 50) for c in cb))
        draw.ellipse([x - size/2, y - size/2, x + size/2, y + size/2], fill=glow_col)


def _draw_rings(draw, t, palette):
    cx, cy = WIDTH // 2, HEIGHT // 2
    for i in range(5):
        rx, ry = 300 + i * 80, 200 + i * 50
        rot    = math.radians(t * 3 + i * 20)
        cr, sr = math.cos(rot), math.sin(rot)
        pts    = []
        for deg in range(0, 361, 5):
            rad = math.radians(deg)
            ex  = rx * math.cos(rad)
            ey  = ry * math.sin(rad)
            pts.append((cx + ex * cr - ey * sr, cy + ex * sr + ey * cr))
        if len(pts) > 1:
            try:
                draw.line(pts, fill=palette[i % len(palette)], width=2)
            except Exception:
                pass


def _apply_vignette(img: Image.Image) -> Image.Image:
    vignette = Image.new("L", (WIDTH, HEIGHT), 0)
    v        = ImageDraw.Draw(vignette)
    steps    = 40
    max_m    = min(WIDTH, HEIGHT) // 2 - 1

    for i in range(steps):
        f      = i / steps
        gray   = int(255 * f)
        margin = int((1 - f) * max_m)
        x0, y0 = max(0, margin), max(0, margin)
        x1, y1 = max(x0 + 1, WIDTH - margin), max(y0 + 1, HEIGHT - margin)
        v.rectangle([x0, y0, x1, y1], fill=gray)

    vignette = vignette.filter(ImageFilter.GaussianBlur(60))
    black    = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    return Image.composite(img, black, vignette)


def _draw_text_overlay(draw, img, t, duration, channel_name, song_title, artist):
    try:
        font_xl  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        font_lg  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
        font_md  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        font_sm  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except Exception:
        font_xl = font_lg = font_md = font_sm = ImageFont.load_default()

    pulse = int(220 + 35 * math.sin(t * 0.8))
    cx    = WIDTH // 2

    # Background pill
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    od      = ImageDraw.Draw(overlay)
    bw, bh  = 1100, 500
    bx, by  = cx - bw // 2, HEIGHT // 2 - bh // 2
    od.rounded_rectangle([bx, by, bx + bw, by + bh], radius=30, fill=(0, 0, 0, 140))
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"), (0, 0))
    draw = ImageDraw.Draw(img)

    def put(text, font, y, color=(255, 255, 255), opacity=None):
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw   = bbox[2] - bbox[0]
        except Exception:
            tw = len(text) * 20
        x = cx - tw // 2
        draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0, 100))
        draw.text((x, y), text, font=font, fill=color + ((opacity or pulse),))

    y = HEIGHT // 2 - 220
    put(f"♫  {channel_name}  ♫", font_md, y, color=(200, 170, 255), opacity=200)
    y += 55
    draw.line([cx - 400, y, cx + 400, y], fill=(255, 255, 255, 60), width=1)
    y += 18

    # Wrap title if needed
    title_lines = _wrap_text(song_title, font_xl, 900, draw)
    for line in title_lines:
        put(line, font_xl, y)
        y += 90

    y += 10
    put(artist, font_lg, y, color=(200, 230, 255), opacity=190)
    y += 65
    draw.line([cx - 300, y, cx + 300, y], fill=(255, 255, 255, 60), width=1)
    y += 18
    put("✦  Slowed  +  Reverb  ✦", font_sm, y, color=(255, 200, 255), opacity=210)

    # Progress bar
    progress = min(t / duration, 1.0)
    bar_y    = HEIGHT - 20
    draw.rectangle([0, bar_y, WIDTH, HEIGHT], fill=(0, 0, 0, 120))
    if progress > 0:
        draw.rectangle([0, bar_y + 4, int(WIDTH * progress), HEIGHT - 4],
                       fill=(180, 100, 255, 200))


def _wrap_text(text: str, font, max_width: int, draw) -> list:
    """Wrap text into lines if too long."""
    try:
        bbox   = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
    except Exception:
        text_w = len(text) * 40

    if text_w <= max_width:
        return [text]

    # Split and wrap
    words = text.split()
    lines = []
    current = []

    for word in words:
        test = " ".join(current + [word])
        try:
            bbox   = draw.textbbox((0, 0), test, font=font)
            test_w = bbox[2] - bbox[0]
        except Exception:
            test_w = len(test) * 40

        if test_w <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]

    if current:
        lines.append(" ".join(current))

    # Max 2 lines, truncate if needed
    if len(lines) > 2:
        lines = lines[:2]
        lines[1] = lines[1][:35] + "…"

    return lines


def _add_grain(img: Image.Image, intensity: int = 8) -> Image.Image:
    arr   = np.array(img).astype(np.int16)
    noise = np.random.randint(-intensity, intensity, arr.shape, dtype=np.int16)
    return Image.fromarray(np.clip(arr + noise, 0, 255).astype(np.uint8))


def _lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _safe(s: str) -> str:
    return re.sub(r"[^\w\-]", "_", s)[:40]
