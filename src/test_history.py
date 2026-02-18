"""
test_history.py
Quick test to verify upload_history.txt is working.
Run this locally: python test_history.py
"""

from pathlib import Path
from datetime import datetime

HISTORY_LOG = Path("output/upload_history.txt")

def test_write():
    print("Testing upload_history.txt...")
    
    # Create output dir
    HISTORY_LOG.parent.mkdir(exist_ok=True)
    
    # Write test entry
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    with open(HISTORY_LOG, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*70}\n")
        f.write(f"Uploaded: {timestamp}\n")
        f.write(f"Language: TEST\n")
        f.write(f"Title:    Test Song\n")
        f.write(f"Artist:   Test Artist\n")
        f.write(f"Video ID: TEST123\n")
        f.write(f"URL:      https://youtube.com/watch?v=TEST123\n")
        f.write(f"{'='*70}\n")
    
    print(f"✅ Written to: {HISTORY_LOG.absolute()}")
    print(f"✅ File size: {HISTORY_LOG.stat().st_size} bytes")
    print("\nContents:")
    print(HISTORY_LOG.read_text())

if __name__ == "__main__":
    test_write()
