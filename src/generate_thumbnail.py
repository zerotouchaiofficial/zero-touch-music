"""
generate_thumbnail.py
Creates a stunning, click-worthy YouTube thumbnail (1280×720).
Design: bold gradient, glowing text, subtle background art, channel branding.
"""

import math
import random
import logging
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

log = logging.getLogger("yt-uploader")

THUMB_W, THUMB_H = 1280, 720

GRADIENT_SETS = [
    # (top-left, bottom-right, accent)
    [(30, 0, 80),   (120, 0, 180),  (255, 100, 255)],
    [(0, 20, 80),   (0, 100, 200),  (0, 220, 255)],
    [(60, 0, 0),    (180, 40, 0),   (255, 160, 0)],
    [(0, 40, 30),   (0, 120, 80),   (80, 255, 180)],
]


def generate_thumbnail(song_title: str, artist: str,
                       channel_name: str, output_dir: str) -> str:
    """
    Creates and saves a YouTube thumbnail.
    Returns path to the saved .jpg file.
    """
    palette = random.choice(GRADIENT_SETS)
    c1, c2, accent = palette

    img = Image.new("RGB", (THUMB_W, THUMB_H))
    draw = ImageDraw.Draw(img)

    # ── 1. Diagonal gradient background ─────────────────────────────
    for y in range(THUMB_H):
        for x in range(THUMB_W):
            t = (x / THUMB_W * 0.5 + y / THUMB_H * 0.5)
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            draw.point((x, y), fill=(r, g, b))

    # ── 2. Glowing orb center-left ───────────────────────────────────
    orb_x, orb_y = THUMB_W // 3, THUMB_H // 2
    for r in range(300, 0, -10):
        alpha = int(30 * (1 - r / 300))
        color = tuple(min(255, c + 80) for c in accent)
        _draw_circle_alpha(draw, orb_x, orb_y, r, color, alpha)

    # ── 3. Geometric accent lines ─────────────────────────────────────
    for i in range(8):
        angle = math.radians(i * 22.5)
        length = 400
        x1 = orb_x + math.cos(angle) * 50
        y1 = orb_y + math.sin(angle) * 50
        x2 = orb_x + math.cos(angle) * length
        y2 = orb_y + math.sin(angle) * length
        draw.line([(x1, y1), (x2, y2)], fill=accent + (40,), width=2)

    # ── 4. Decorative music note / wave graphic ───────────────────────
    _draw_waveform(draw, accent, y_center=THUMB_H // 2)

    # ── 5. Right-side dark panel for text readability ─────────────────
    overlay = Image.new("RGBA", (THUMB_W, THUMB_H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rectangle([THUMB_W // 2, 0, THUMB_W, THUMB_H], fill=(0, 0, 0, 160))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # ── 6. Vignette ───────────────────────────────────────────────────
    img = _vignette(img)
    draw = ImageDraw.Draw(img)

    # ── 7. Text ───────────────────────────────────────────────────────
    try:
        font_title   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 90)
        font_artist  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 52)
        font_badge   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        font_channel = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    except Exception:
        font_title = font_artist = font_badge = font_channel = ImageFont.load_default()

    text_cx = THUMB_W * 3 // 4  # center of right panel

    def centered_text(text, font, y, color=(255, 255, 255)):
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
        except Exception:
            tw = len(text) * 20
        x = text_cx - tw // 2
        # Shadow
        draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0))
        draw.text((x, y), text, font=font, fill=color)

    # "SLOWED + REVERB" badge
    badge_y = 90
    badge_text = "◆  SLOWED + REVERB  ◆"
    try:
        bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
        bw, bh = bbox[2] - bbox[0] + 40, bbox[3] - bbox[1] + 20
    except Exception:
        bw, bh = 400, 60
    bx = text_cx - bw // 2
    draw.rounded_rectangle([bx, badge_y, bx + bw, badge_y + bh],
                            radius=15, fill=accent + (0,) if len(accent) == 3 else accent)
    draw.rounded_rectangle([bx, badge_y, bx + bw, badge_y + bh],
                            radius=15, fill=tuple(min(255, c + 30) for c in accent))
    centered_text(badge_text, font_badge, badge_y + 8, color=(0, 0, 0))

    # Song title (possibly wrap)
    title_display = song_title if len(song_title) <= 18 else song_title[:16] + "…"
    centered_text(title_display, font_title, 200, color=(255, 255, 255))

    # Artist
    centered_text(f"— {artist} —", font_artist, 320, color=(200, 220, 255))

    # Divider
    line_y = 400
    draw.line([text_cx - 250, line_y, text_cx + 250, line_y],
              fill=(255, 255, 255, 100), width=2)

    # Channel name at bottom
    centered_text(f"♫  {channel_name}", font_channel, 430, color=(180, 180, 255))

    # ── 8. Corner watermark / border ──────────────────────────────────
    draw.rectangle([0, 0, THUMB_W - 1, THUMB_H - 1], outline=accent, width=6)

    # ── Save ──────────────────────────────────────────────────────────
    out_path = Path(output_dir) / f"{_safe(song_title)}_thumbnail.jpg"
    img.save(str(out_path), "JPEG", quality=95, optimize=True)
    log.info(f"  ✓ Thumbnail saved: {out_path.name}")
    return str(out_path)


def _draw_circle_alpha(draw, cx, cy, r, color, alpha):
    """Draw a filled circle with a given alpha (faked via color blending)."""
    blended = tuple(min(255, c + alpha) for c in color[:3])
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=blended)


def _draw_waveform(draw, accent, y_center):
    """Draw a stylized audio waveform in the left panel."""
    bars = 40
    bar_w = 8
    spacing = 14
    start_x = 80
    max_h = 200

    for i in range(bars):
        height = int(max_h * abs(math.sin(i * 0.35)) * random.uniform(0.5, 1.0))
        x = start_x + i * (bar_w + spacing)
        color = tuple(min(255, c + 60) for c in accent)
        draw.rectangle(
            [x, y_center - height // 2, x + bar_w, y_center + height // 2],
            fill=color + (180,) if len(color) == 4 else color,
        )


def _vignette(img: Image.Image) -> Image.Image:
    vignette = Image.new("L", (THUMB_W, THUMB_H), 0)
    v = ImageDraw.Draw(vignette)
    steps = 40
    for i in range(steps):
        f = i / steps
        margin = int((1 - f) * min(THUMB_W, THUMB_H) * 0.6)
        v.rectangle([margin, margin, THUMB_W - margin, THUMB_H - margin], fill=int(255 * f))
    vignette = vignette.filter(ImageFilter.GaussianBlur(60))
    black = Image.new("RGB", (THUMB_W, THUMB_H), (0, 0, 0))
    return Image.composite(img, black, vignette)


def _safe(s: str) -> str:
    import re
    return re.sub(r"[^\w\-]", "_", s)[:40]
