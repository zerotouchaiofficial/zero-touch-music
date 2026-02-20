"""
seo_generator.py
Generates SEO metadata for regular songs and mashups
"""

import random
from datetime import datetime

# Regular song titles
TITLE_TEMPLATES = [
    "{title} - {artist} (Slowed + Reverb) 🌙",
    "{title} [Slowed + Reverb] | {artist} ✨",
    "{title} (Slowed to Perfection + Reverb) ~ {artist}",
    "🌊 {title} - {artist} | Slowed + Reverb",
    "{title} ♾ Slowed & Reverb | {artist} 💫",
]

# Mashup titles
MASHUP_TEMPLATES = [
    "{title} [Slowed + Reverb Mashup] 🎛️",
    "{title} (Slowed + Reverb Mashup) ✨",
    "🎵 {title} | Slowed + Reverb Mashup",
    "{title} ~ Slowed & Reverb Mashup 🌙",
]

DESCRIPTION_TEMPLATE = """🎵 {title} (Slowed + Reverb)
👤 Original Artist: {artist}
🎬 Channel: {channel_name}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ About This Edit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{description_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📜 Credits
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{credits}
🔗 Original: {original_url}
🎛️  Audio Edit: {channel_name}
📅 Uploaded: {date}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚖️  Copyright Disclaimer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is a fan-made edit for entertainment. All rights belong to the original artists and their labels. No copyright infringement intended. If you are the copyright owner and wish this removed, please contact us.

Under Section 107 of the Copyright Act 1976, allowance is made for "fair use" for transformation and commentary.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔔 Support
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Like, Subscribe, Share
✅ Turn on notifications for daily uploads

{hashtags}
"""

BASE_TAGS = [
    "slowed and reverb",
    "slowed reverb",
    "lofi",
    "slowed songs",
    "aesthetic music",
    "chill music",
    "trending songs 2025",
    "viral songs",
]

MASHUP_TAGS = [
    "mashup",
    "song mashup",
    "slowed mashup",
    "reverb mashup",
    "music mashup",
]

HASHTAGS = ["#slowedreverb", "#lofi", "#aesthetic", "#trending2025"]


def generate_seo_metadata(song_title: str, artist: str, channel_name: str, 
                         original_url: str, is_mashup: bool = False) -> dict:
    """
    Generates SEO-optimized metadata.
    
    is_mashup: True if this is a mashup (title already contains " x ")
    """
    
    # Detect if mashup automatically
    if " x " in song_title or " X " in song_title:
        is_mashup = True
    
    # Generate title
    if is_mashup:
        template = random.choice(MASHUP_TEMPLATES)
        yt_title = template.format(title=song_title)
    else:
        template = random.choice(TITLE_TEMPLATES)
        yt_title = template.format(title=song_title, artist=artist)
    
    if len(yt_title) > 100:
        yt_title = yt_title[:97] + "..."
    
    # Generate description text
    if is_mashup:
        description_text = f"""This is a mashup of two trending songs slowed to 80% with reverb, creating a dreamy, lofi aesthetic. Perfect for studying, late-night drives, or just vibing. 🌙

The songs blend seamlessly with a smooth crossfade, giving you the best of both tracks in one unique experience."""
        credits = f"🎤 Mashup: {song_title}\n🎸 Original Artists: {artist}"
    else:
        description_text = f"""This is a slowed + reverb version of "{song_title}" by {artist}. The audio has been slowed to 80% and enhanced with warm reverb for a dreamy, lofi aesthetic — perfect for studying, late-night drives, or just vibing. 🌙"""
        credits = f"🎤 Original Song: {song_title}\n🎸 Artist: {artist}"
    
    description = DESCRIPTION_TEMPLATE.format(
        title=song_title,
        artist=artist,
        channel_name=channel_name,
        description_text=description_text,
        credits=credits,
        original_url=original_url,
        date=datetime.utcnow().strftime("%B %d, %Y"),
        hashtags=" ".join(random.sample(HASHTAGS, min(4, len(HASHTAGS)))),
    )
    
    # Generate tags
    if is_mashup:
        song_tags = [
            song_title[:30],
            f"{song_title} mashup"[:30],
        ]
        # If title has " x ", extract both song names
        if " x " in song_title.lower():
            parts = song_title.lower().split(" x ")
            if len(parts) == 2:
                song_tags.extend([
                    parts[0].strip()[:30],
                    parts[1].strip()[:30],
                    f"{parts[0].strip()} {parts[1].strip()}"[:30],
                ])
        all_tags = song_tags + MASHUP_TAGS + BASE_TAGS
    else:
        song_tags = [
            song_title[:30],
            f"{song_title} slowed"[:30],
            artist[:30],
            f"{artist} slowed"[:30],
        ]
        all_tags = song_tags + BASE_TAGS
    
    # Validate and dedupe
    valid_tags = []
    total_chars = 0
    seen = set()
    
    for tag in all_tags:
        tag = tag.strip()
        if not tag or len(tag) > 30 or tag.lower() in seen:
            continue
        if total_chars + len(tag) > 450:
            break
        valid_tags.append(tag)
        seen.add(tag.lower())
        total_chars += len(tag)
        if len(valid_tags) >= 25:
            break
    
    return {
        "title":       yt_title,
        "description": description,
        "tags":        valid_tags,
    }
