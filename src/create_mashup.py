"""
create_mashup.py
Creates mashups by blending two songs together with crossfade.
"""

import logging
from pathlib import Path
from pydub import AudioSegment

log = logging.getLogger("yt-uploader")


def create_mashup(audio1_path: str, audio2_path: str, output_dir: str, 
                  song1_title: str, song2_title: str) -> str:
    """
    Creates a mashup by crossfading two audio files.
    Returns path to the mashup audio file.
    """
    log.info(f"  Creating mashup: '{song1_title}' x '{song2_title}'")
    
    # Load both audio files
    audio1 = AudioSegment.from_file(audio1_path)
    audio2 = AudioSegment.from_file(audio2_path)
    
    # Normalize volumes
    audio1 = audio1.normalize()
    audio2 = audio2.normalize()
    
    # Get lengths
    len1 = len(audio1)
    len2 = len(audio2)
    
    # Strategy: Play first half of song1, crossfade to song2, play rest of song2
    crossfade_duration = 5000  # 5 second crossfade
    
    # Calculate split points
    split1 = len1 // 2
    split2 = len2 // 2
    
    # Get segments
    part1 = audio1[:split1]
    part1_tail = audio1[split1:split1 + crossfade_duration]
    
    part2_head = audio2[split2 - crossfade_duration:split2]
    part2 = audio2[split2:]
    
    # Crossfade the middle parts
    crossfaded = part1_tail.append(part2_head, crossfade=crossfade_duration)
    
    # Combine all parts
    mashup = part1 + crossfaded + part2
    
    # Apply fade in/out
    mashup = mashup.fade_in(3000).fade_out(4000)
    
    # Export
    output_path = Path(output_dir) / f"mashup_{_safe(song1_title)}_{_safe(song2_title)}.mp3"
    mashup.export(str(output_path), format="mp3", bitrate="320k")
    
    log.info(f"  ✓ Mashup created: {output_path.name} ({len(mashup)/1000:.1f}s)")
    return str(output_path)


def _safe(s: str) -> str:
    import re
    return re.sub(r"[^\w\-]", "_", s)[:20]
