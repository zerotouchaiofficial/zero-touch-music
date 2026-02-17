"""
seo_generator.py
Generates fully optimized YouTube title, description, and tags
for maximum discoverability in the Slowed+Reverb niche.
"""

import random
from datetime import datetime

# ─── Title Templates ────────────────────────────────────────────────────────────
TITLE_TEMPLATES = [
    "{title} - {artist} (Slowed + Reverb) 🌙",
    "{title} [Slowed + Reverb] | {artist} ✨",
    "{title} (Slowed to Perfection + Reverb) ~ {artist}",
    "🌊 {title} - {artist} | Slowed + Reverb Version",
    "{title} ♾ Slowed & Reverb | {artist} 💫",
    "「{title}」- Slowed + Reverb 🎧 | {artist}",
]

# ─── Description Template ────────────────────────────────────────────────────────
DESCRIPTION_TEMPLATE = """🎵 {title} (Slowed + Reverb)
👤 Original Artist: {artist}
🎬 Channel: {channel_name}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ About This Edit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is a slowed + reverb version of "{title}" by {artist}.
The audio has been slowed to 80% of the original speed and enhanced with a warm,
spacious reverb to give it a dreamy, lofi aesthetic — perfect for studying,
late-night drives, relaxing, or just vibing. 🌙

The visual is crafted with a cinematic animated background for the ultimate
immersive listening experience.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎧 Best Experienced With
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Headphones or earphones
• Lights dimmed
• Late at night ✨

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📜 Credits
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎤 Original Song  : {title}
🎸 Artist         : {artist}
🔗 Original Video : {original_url}
🎛️  Audio Edit     : {channel_name} (Slowed + Reverb)
🎨 Visual Design  : {channel_name} Team
📅 Uploaded       : {date}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚖️  Copyright Disclaimer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This video is a fan-made edit for entertainment purposes only.
All rights to the original song belong to {artist} and their label.
No copyright infringement is intended. If you are the copyright owner
and wish this video removed, please contact us and we will take immediate action.

Under Section 107 of the Copyright Act 1976, allowance is made for
"fair use" for purposes such as commentary, education, and transformation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔔 Support Us
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
If you enjoy this vibe, please:
✅ Like the video
✅ Subscribe for daily slowed + reverb drops
✅ Turn on notifications so you never miss a release
✅ Share with a friend who loves this aesthetic 🌊

🎵 Subscribe: @{channel_name_safe}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔎 Tags (ignore)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{hashtags}
"""

# ─── Tag pools ───────────────────────────────────────────────────────────────────
BASE_TAGS = [
    "slowed and reverb", "slowed reverb", "lofi", "lofi music",
    "slowed songs", "reverb songs", "aesthetic music", "night drive music",
    "chill music", "relaxing music", "study music", "lofi beats",
    "slowed version", "slowed to perfection", "bass boosted",
    "trending songs 2025", "viral songs 2025", "best songs 2025",
    "music 2025", "new songs 2025", "top hits 2025",
    "slowed music", "reverb music", "dreamy music",
    "late night music", "bedroom pop", "dark aesthetic",
    "vibe music", "emotional songs", "sad songs slowed",
]

HASHTAG_POOL = [
    "#slowedreverb", "#lofi", "#aesthetic", "#chillmusic",
    "#slowedmusic", "#vibes", "#latenight", "#studymusic",
    "#trending2025", "#newmusic2025", "#viral", "#slowedversion",
    "#musicaesthetic", "#reverbmusic", "#relaxingmusic",
]


def generate_seo_metadata(song_title: str, artist: str,
                           channel_name: str, original_url: str) -> dict:
    """
    Returns { title, description, tags }
    """
    # Title
    template = random.choice(TITLE_TEMPLATES)
    yt_title  = template.format(title=song_title, artist=artist)
    # YouTube title limit is 100 chars
    if len(yt_title) > 100:
        yt_title = yt_title[:97] + "..."

    # Tags: base + song-specific
    song_tags = [
        song_title,
        f"{song_title} slowed",
        f"{song_title} reverb",
        f"{song_title} slowed reverb",
        f"{song_title} {artist}",
        artist,
        f"{artist} slowed",
        f"{artist} songs",
    ]
    all_tags = song_tags + random.sample(BASE_TAGS, min(20, len(BASE_TAGS)))
    all_tags = list(dict.fromkeys(all_tags))[:500]  # dedupe, max 500 tags chars-wise

    # Hashtags for description footer
    song_hashtags = [
        f"#{song_title.replace(' ', '')}",
        f"#{artist.replace(' ', '')}",
        f"#{song_title.replace(' ', '')}SlowedReverb",
    ]
    hashtags = " ".join(song_hashtags + random.sample(HASHTAG_POOL, 8))

    channel_safe = channel_name.replace(" ", "")

    description = DESCRIPTION_TEMPLATE.format(
        title=song_title,
        artist=artist,
        channel_name=channel_name,
        channel_name_safe=channel_safe,
        original_url=original_url,
        date=datetime.utcnow().strftime("%B %d, %Y"),
        hashtags=hashtags,
    )

    return {
        "title":       yt_title,
        "description": description,
        "tags":        all_tags,
    }
