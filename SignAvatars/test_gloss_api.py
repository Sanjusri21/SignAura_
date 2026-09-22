"""
Test suite for SignAvatars Gloss -> Animation API endpoints.
Tests /motions, /motions/{gloss}, /motions/search/{query}, /motion/{gloss}, and canonical variant resolution.
"""

import os
import sys
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from api import app

client = TestClient(app)

def run_tests():
    print("=" * 60)
    print("TESTING SIGNAVATARS GLOSS -> ANIMATION API")
    print("=" * 60)

    # 1. Health & Root Check
    print("\n1. Testing GET /health and GET / ...")
    r_root = client.get("/")
    assert r_root.status_code == 200, f"Root failed: {r_root.status_code}"
    print(f"  GET / -> {r_root.json()}")

    r_health = client.get("/health")
    assert r_health.status_code == 200, f"Health failed: {r_health.status_code}"
    print(f"  GET /health -> {r_health.json()}")

    # 2. List motions (GET /motions)
    print("\n2. Testing GET /motions ...")
    r_motions = client.get("/motions")
    assert r_motions.status_code == 200, f"List motions failed: {r_motions.status_code}"
    motions_data = r_motions.json()
    print(f"  Count: {motions_data['count']}")
    for m in motions_data["motions"]:
        print(f"    - {m['gloss']} (key: {m.get('motion_key')}): frames={m['frames']}, fps={m['fps']}, vertices={m['vertex_count']}")
    assert motions_data["count"] >= 5, f"Expected at least 5 motions, got {motions_data['count']}"

    # 3. Search motions (GET /motions/search/sample)
    print("\n3. Testing GET /motions/search/sample ...")
    r_search = client.get("/motions/search/sample")
    assert r_search.status_code == 200, f"Search failed: {r_search.status_code}"
    search_data = r_search.json()
    print(f"  Query: '{search_data['query']}', Matches: {search_data['count']}")
    assert search_data["count"] >= 1, "Expected match for 'sample'"
    assert any(m["motion_key"] == "sample_1" for m in search_data["matches"])

    # 4. Canonical gloss metadata for 'help' -> resolves to help_2
    print("\n4. Testing GET /motions/help (Canonical Resolution -> help_2) ...")
    r_help = client.get("/motions/help")
    assert r_help.status_code == 200, f"Metadata help failed: {r_help.status_code}"
    help_meta = r_help.json()
    print(f"  help metadata: gloss='{help_meta.get('gloss')}', motion_key='{help_meta.get('motion_key')}', frames={help_meta.get('frames')}")
    assert help_meta["frames"] == 141, f"Expected 141 frames for help, got {help_meta['frames']}"
    assert help_meta["motion_key"] == "help_2"

    # 5. Canonical gloss metadata for 'teacher' -> resolves to teacher_2
    print("\n5. Testing GET /motions/teacher (Canonical Resolution -> teacher_2) ...")
    r_teacher = client.get("/motions/teacher")
    assert r_teacher.status_code == 200, f"Metadata teacher failed: {r_teacher.status_code}"
    teacher_meta = r_teacher.json()
    print(f"  teacher metadata: gloss='{teacher_meta.get('gloss')}', motion_key='{teacher_meta.get('motion_key')}', frames={teacher_meta.get('frames')}")
    assert teacher_meta["frames"] == 108, f"Expected 108 frames for teacher, got {teacher_meta['frames']}"
    assert teacher_meta["motion_key"] == "teacher_2"

    # 6. Binary motion data for canonical 'help' (GET /motion/help -> streams help_2.npy)
    print("\n6. Testing GET /motion/help (Binary Stream) ...")
    r_bin_help = client.get("/motion/help")
    assert r_bin_help.status_code == 200, f"Binary help failed: {r_bin_help.status_code}"
    expected_help_bytes = 141 * 10475 * 3 * 4
    assert len(r_bin_help.content) == expected_help_bytes, f"Size mismatch for help: {len(r_bin_help.content)} vs {expected_help_bytes}"
    assert r_bin_help.headers.get("x-frames") == "141"
    print(f"  Binary /motion/help: {len(r_bin_help.content)} bytes, {r_bin_help.headers.get('x-frames')} frames, FPS {r_bin_help.headers.get('x-fps')}")

    # 7. Binary motion data for canonical 'teacher' (GET /motion/teacher -> streams teacher_2.npy)
    print("\n7. Testing GET /motion/teacher (Binary Stream) ...")
    r_bin_teacher = client.get("/motion/teacher")
    assert r_bin_teacher.status_code == 200, f"Binary teacher failed: {r_bin_teacher.status_code}"
    expected_teacher_bytes = 108 * 10475 * 3 * 4
    assert len(r_bin_teacher.content) == expected_teacher_bytes
    assert r_bin_teacher.headers.get("x-frames") == "108"
    print(f"  Binary /motion/teacher: {len(r_bin_teacher.content)} bytes, {r_bin_teacher.headers.get('x-frames')} frames, FPS {r_bin_teacher.headers.get('x-fps')}")

    # 8. Binary motion data for 'good' and 'drink' and 'go'
    for test_word, exp_frames in [("good", 109), ("drink", 143), ("go", 107), ("ishbosheth", 51), ("sample_1", 141)]:
        print(f"\n8. Testing GET /motion/{test_word} ...")
        r_bin = client.get(f"/motion/{test_word}")
        assert r_bin.status_code == 200, f"Binary {test_word} failed: {r_bin.status_code}"
        exp_bytes = exp_frames * 10475 * 3 * 4
        assert len(r_bin.content) == exp_bytes, f"Size mismatch for {test_word}: {len(r_bin.content)} vs {exp_bytes}"
        assert r_bin.headers.get("x-frames") == str(exp_frames)
        print(f"  OK: {test_word} -> {len(r_bin.content)} bytes ({exp_frames} frames)")

    # 9. Error handling: Non-existent gloss
    print("\n9. Testing Error Handling for 404 (non-existent gloss) ...")
    r_404_meta = client.get("/motions/nonexistent_gloss_12345")
    assert r_404_meta.status_code == 404, f"Expected 404, got {r_404_meta.status_code}"

    r_404_bin = client.get("/motion/nonexistent_gloss_12345")
    assert r_404_bin.status_code == 404, f"Expected 404, got {r_404_bin.status_code}"
    print("  OK: 404 handled gracefully for nonexistent gloss")

    # 10. Security test: Path traversal attempts
    print("\n10. Testing Security: Path traversal rejection ...")
    r_traversal = client.get("/motions/..%2f..%2fetc%2fpasswd")
    assert r_traversal.status_code in [400, 404]
    print(f"  OK: Path traversal blocked ({r_traversal.status_code})")

    print("\n" + "=" * 60)
    print("ALL API TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
