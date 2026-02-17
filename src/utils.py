"""
utils.py
Shared utilities: logging setup, cleanup, file helpers.
"""

import logging
import shutil
from pathlib import Path


def setup_logging(level=logging.INFO) -> logging.Logger:
    log = logging.getLogger("yt-uploader")
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        ))
        log.addHandler(handler)
    log.setLevel(level)
    return log


def cleanup_temp_files(temp_dir: str):
    """Remove all files in the temp directory."""
    p = Path(temp_dir)
    if p.exists():
        for f in p.iterdir():
            try:
                f.unlink()
            except Exception:
                pass


def safe_filename(s: str, max_len: int = 60) -> str:
    import re
    return re.sub(r"[^\w\-]", "_", s)[:max_len]
