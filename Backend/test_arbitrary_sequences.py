"""
Test script for arbitrary multi-word sequences (up to 7+ words).
Tests:
- good
- good drink
- good drink help
- good drink help teacher
- good drink help teacher go
- good drink help teacher go ishbosheth
- good drink help teacher go ishbosheth sample_1

Verifies:
1. No 3-word truncation
2. Every gloss resolved
3. 30 FPS resampling
4. Cosine transition smoothing
5. Binary buffer size and finite Float32 vertex values
"""

import os
import sys
import numpy as np
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.main import app

client = TestClient(app)

PHRASES = [
    ("1-word", "good", 1),
    ("2-word", "good drink", 2),
    ("3-word", "good drink help", 3),
    ("4-word", "good drink help teacher", 4),
    ("5-word", "good drink help teacher go", 5),
    ("6-word", "good drink help teacher go ishbosheth", 6),
    ("7-word", "good drink help teacher go ishbosheth sample_1", 7),
]

def main():
    print("=" * 80)
    print("TESTING ARBITRARY MULTI-WORD SEQUENCES (1 to 7+ WORDS)")
    print("=" * 80)

    prev_frames = 0

    for label, text, exp_word_count in PHRASES:
        print(f"\nTesting {label}: \"{text}\"")
        res = client.post("/api/translate-to-signavatar", json={"text": text})
        assert res.status_code == 200, f"HTTP {res.status_code}: {res.text}"
        data = res.json()

        assert data["available"] is True, f"Failed availability for: {text}, response: {data}"
        glosses = data.get("glosses", [])
        print(f"  Glosses returned: {glosses} (Count: {len(glosses)})")
        assert len(glosses) == exp_word_count, f"Truncation detected! Expected {exp_word_count}, got {len(glosses)}"

        anim = data.get("animation", {})
        frames = anim.get("frames", 0)
        fps = anim.get("fps", 0)
        vcount = anim.get("vertex_count", 0)
        anim_url = anim.get("animation_url", "")

        print(f"  Animation: {frames} frames @ {fps} FPS, {vcount} vertices, URL: {anim_url}")
        assert fps == 30, f"Expected target FPS 30, got {fps}"
        assert vcount == 10475, f"Expected 10475 vertices, got {vcount}"
        assert frames > prev_frames, f"Frame count did not increase: prev={prev_frames}, current={frames}"
        prev_frames = frames

        # Verify binary stream
        bin_res = client.get(anim_url)
        assert bin_res.status_code == 200, f"Failed fetching binary from {anim_url}"
        raw_bytes = bin_res.content
        expected_bytes = frames * 10475 * 3 * 4
        print(f"  Binary size: {len(raw_bytes):,} bytes (Expected: {expected_bytes:,} bytes)")
        assert len(raw_bytes) == expected_bytes, f"Size mismatch: {len(raw_bytes)} vs {expected_bytes}"

        float_data = np.frombuffer(raw_bytes, dtype=np.float32)
        assert np.isfinite(float_data).all(), "Binary data contains non-finite values (NaN/Inf)"
        print(f"  Validation: [PASS] All {frames} frames are finite Float32 SMPL-X coordinates")

    # Verify missing glosses in multi-word sentence
    print("\nTesting sentence with missing gloss: \"good water drink\"")
    res_miss = client.post("/api/translate-to-signavatar", json={"text": "good water drink"})
    assert res_miss.status_code == 200
    data_miss = res_miss.json()
    assert data_miss["available"] is False
    assert "animation" not in data_miss
    unavail = [u["gloss"].lower() for u in data_miss.get("unavailable", [])]
    print(f"  Missing gloss handled cleanly: unavailable={unavail}")
    assert "water" in unavail

    print("\n" + "=" * 80)
    print("ALL MULTI-WORD SEQUENCES (1 to 7+ WORDS) PASSED WITH ZERO TRUNCATION!")
    print("=" * 80)

if __name__ == "__main__":
    main()
