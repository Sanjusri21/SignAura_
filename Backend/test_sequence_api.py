"""
Comprehensive test suite for the SignAura Backend Sequence API (STEP 7).
Tests:
- POST /api/signavatar/sequence with valid glosses (sample_1 + ishbosheth)
- GET /api/signavatar/sequence/{sequence_id}/metadata (Metadata verification)
- GET /api/signavatar/sequence/{sequence_id} (Binary Float32 buffer streaming & exact byte count)
- Programmatic byte calculation: 144 * 10475 * 3 * 4 = 18,100,800 bytes
- Missing sequence handling (HTTP 404)
- Path traversal rejection (HTTP 400)
- Missing gloss handling (available=false, no sequence generated)
- Step-1 motion regression verification
"""

import os
import sys
import numpy as np
from fastapi.testclient import TestClient

# Ensure Backend directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.main import app

client = TestClient(app)


def test_sequence_api_full_flow():
    print("\n" + "=" * 60)
    print("STEP 7: TESTING BACKEND SEQUENCE API")
    print("=" * 60)

    # -------------------------------------------------------------
    # Test A: Generate sequence POST /api/signavatar/sequence
    # -------------------------------------------------------------
    print("\n--- Test A: Generate Sequence POST /api/signavatar/sequence ---")
    payload = {"glosses": ["sample_1", "ishbosheth"]}
    r_gen = client.post("/api/signavatar/sequence", json=payload)
    assert r_gen.status_code == 200, f"Failed generating sequence: {r_gen.status_code} {r_gen.text}"
    gen_data = r_gen.json()
    print(f"  POST Response: {gen_data}")

    assert gen_data["available"] is True
    assert gen_data["glosses"] == ["sample_1", "ishbosheth"]
    assert gen_data["fps"] == 30
    assert gen_data["frames"] == 144
    assert gen_data["vertex_count"] == 10475
    assert "sequence_id" in gen_data
    assert "animation_url" in gen_data
    assert "metadata_url" in gen_data
    assert gen_data["source"] == "BridgeConn Sign Dictionary ISL"

    seq_id = gen_data["sequence_id"]
    anim_url = gen_data["animation_url"]
    meta_url = gen_data["metadata_url"]

    # -------------------------------------------------------------
    # Test B: Fetch Metadata GET /api/signavatar/sequence/{seq_id}/metadata
    # -------------------------------------------------------------
    print(f"\n--- Test B: Fetch Metadata GET {meta_url} ---")
    r_meta = client.get(meta_url)
    assert r_meta.status_code == 200, f"Failed fetching metadata: {r_meta.status_code} {r_meta.text}"
    meta_data = r_meta.json()
    print(f"  Metadata Response: {meta_data}")

    assert meta_data["available"] is True
    assert meta_data["sequence_id"] == seq_id
    assert meta_data["frames"] == 144
    assert meta_data["fps"] == 30
    assert meta_data["vertex_count"] == 10475
    assert meta_data["vertex_shape"] == [144, 10475, 3]
    assert meta_data["glosses"] == ["sample_1", "ishbosheth"]

    # -------------------------------------------------------------
    # Test C: Fetch Binary Stream GET /api/signavatar/sequence/{seq_id}
    # -------------------------------------------------------------
    print(f"\n--- Test C: Fetch Binary Animation Stream GET {anim_url} ---")
    r_bin = client.get(anim_url)
    assert r_bin.status_code == 200, f"Failed fetching binary stream: {r_bin.status_code}"

    # Verify Response Headers
    headers = r_bin.headers
    print("  Binary Headers:")
    for k in ["Content-Type", "Content-Length", "X-Frames", "X-FPS", "X-Vertices", "X-Components", "X-Dtype", "X-Source"]:
        print(f"    {k}: {headers.get(k)}")

    assert headers.get("Content-Type") == "application/octet-stream"
    assert int(headers.get("X-Frames")) == 144
    assert int(headers.get("X-FPS")) == 30
    assert int(headers.get("X-Vertices")) == 10475
    assert int(headers.get("X-Components")) == 3
    assert headers.get("X-Dtype") == "float32"
    assert headers.get("X-Source") == "BridgeConn Sign Dictionary ISL"

    # PART 4: Programmatic byte size verification
    expected_frames = 144
    expected_vertices = 10475
    expected_components = 3
    bytes_per_float = 4  # float32 = 4 bytes
    expected_byte_count = expected_frames * expected_vertices * expected_components * bytes_per_float

    actual_byte_count = len(r_bin.content)
    print(f"\n  Programmatic Buffer Size Verification:")
    print(f"    Expected: {expected_frames} × {expected_vertices} × {expected_components} × {bytes_per_float} = {expected_byte_count:,} bytes")
    print(f"    Actual  : {actual_byte_count:,} bytes")
    assert actual_byte_count == expected_byte_count, f"Size mismatch! Expected {expected_byte_count}, got {actual_byte_count}"

    # Verify content parsed as Float32 array
    vertex_array = np.frombuffer(r_bin.content, dtype=np.float32).reshape(expected_frames, expected_vertices, expected_components)
    assert vertex_array.shape == (144, 10475, 3)
    assert vertex_array.dtype == np.float32
    assert np.isfinite(vertex_array).all()
    print(f"  Float32 Vertex Buffer loaded cleanly into shape: {vertex_array.shape}, finite=True")

    # -------------------------------------------------------------
    # Test D: Missing Sequence GET -> HTTP 404
    # -------------------------------------------------------------
    print("\n--- Test D: Missing Sequence (404) ---")
    r_404_bin = client.get("/api/signavatar/sequence/nonexistent_sequence_99999")
    assert r_404_bin.status_code == 404
    print("  GET /api/signavatar/sequence/nonexistent -> HTTP 404 [OK]")

    r_404_meta = client.get("/api/signavatar/sequence/nonexistent_sequence_99999/metadata")
    assert r_404_meta.status_code == 404
    print("  GET /api/signavatar/sequence/nonexistent/metadata -> HTTP 404 [OK]")

    # -------------------------------------------------------------
    # Test E: Path Traversal Attempt -> HTTP 400
    # -------------------------------------------------------------
    print("\n--- Test E: Path Traversal Rejection (400) ---")
    traversal_payloads = [
        "../sample_1",
        "..%2Fsample_1",
        "../../etc/passwd",
        "/etc/passwd",
        "C:\\Windows\\System32",
        "sequence_sample_1/../../other"
    ]
    for bad_id in traversal_payloads:
        r_trav = client.get(f"/api/signavatar/sequence/{bad_id}")
        assert r_trav.status_code in [400, 404], f"Expected 400/404 for '{bad_id}', got {r_trav.status_code}"
        print(f"  Traversal attempt '{bad_id}' rejected with HTTP {r_trav.status_code} [OK]")

    # -------------------------------------------------------------
    # Test F: Missing Gloss in Sequence -> available=false, no sequence generated
    # -------------------------------------------------------------
    print("\n--- Test F: Missing Gloss Handling ---")
    r_missing = client.post("/api/signavatar/sequence", json={"glosses": ["sample_1", "hello"]})
    assert r_missing.status_code == 200
    missing_data = r_missing.json()
    print(f"  Missing Gloss Response: {missing_data}")
    assert missing_data["available"] is False
    assert "unavailable" in missing_data
    assert len(missing_data["unavailable"]) == 1
    assert missing_data["unavailable"][0]["gloss"] == "hello"
    assert "animation_url" not in missing_data
    assert "animation_file" not in missing_data

    # -------------------------------------------------------------
    # Test G: Existing Step-1 Motion Endpoint Preservation
    # -------------------------------------------------------------
    print("\n--- Test G: Existing Motion Endpoint Preservation ---")
    r_s1 = client.get("/api/signavatar/motion/sample_1")
    assert r_s1.status_code == 200
    assert r_s1.json()["available"] is True

    r_ish = client.get("/api/signavatar/motion/ishbosheth")
    assert r_ish.status_code == 200
    assert r_ish.json()["available"] is True
    print("  GET /api/signavatar/motion/sample_1 & ishbosheth work properly [OK]")


if __name__ == "__main__":
    test_sequence_api_full_flow()
    print("\n" + "=" * 60)
    print("ALL STEP 7 BACKEND SEQUENCE API TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)
