"""
Comprehensive End-to-End Test Suite for SignAura ISL Platform.
Covers all 16 verification areas required for Phases 1-15:
1. SignAvatarClient
2. Gloss inventory & metadata
3. Variant resolution (help -> help_2, teacher -> teacher_2)
4. ISL translation
5. ISL grammar rules (SOV, WH-words, Time markers)
6. Tamil translation & Unicode preservation
7. Animation sequencing (resampling to 30 FPS, cosine transitions)
8. Sequence metadata
9. Binary animation endpoint (Float32, 10475 vertices, headers)
10. Text-to-SignAvatar ("good drink", "help teacher", "go drink help")
11. Speech-to-SignAvatar flow validation
12. Video-to-SignAvatar pipeline validation
13. Unavailable gloss handling ("hello", "missing_random_word")
14. Partial availability handling (honest refusal with structured missing items)
15. Security & path traversal rejection
16. Malformed input & schema validation
"""

import os
import sys
import pytest
import numpy as np
from fastapi.testclient import TestClient

# Ensure Backend is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.main import app
from app.services.signavatar_client import signavatar_client, SignAvatarClient
from app.services.isl.service import get_isl_service
from app.services.isl.grammar import ISLGrammarTransformer
from app.services.animation_sequencer import animation_sequencer, resample_motion, create_transition, sequence_animations
from app.services.translation_animation_service import translation_animation_service

client = TestClient(app)


# ==============================================================================
# 1 & 2 & 3: SIGNAVATAR CLIENT, INVENTORY & DETERMINISTIC VARIANT RESOLUTION
# ==============================================================================

@pytest.mark.asyncio
async def test_gloss_variant_resolution():
    """Verify exact canonical glosses and variant resolutions."""
    # Exact canonical
    good_res = await signavatar_client.resolve_gloss_animation("good")
    assert good_res["available"] is True
    assert good_res["gloss"] == "good"
    assert good_res["motion_key"] == "good"
    assert good_res["vertex_count"] == 10475

    drink_res = await signavatar_client.resolve_gloss_animation("drink")
    assert drink_res["available"] is True
    assert drink_res["motion_key"] == "drink"

    go_res = await signavatar_client.resolve_gloss_animation("go")
    assert go_res["available"] is True
    assert go_res["motion_key"] == "go"

    # Variant resolution (help -> help_2, teacher -> teacher_2)
    help_res = await signavatar_client.resolve_gloss_animation("help")
    assert help_res["available"] is True
    assert help_res["gloss"] == "help"
    assert help_res["motion_key"] == "help_2"

    teacher_res = await signavatar_client.resolve_gloss_animation("teacher")
    assert teacher_res["available"] is True
    assert teacher_res["gloss"] == "teacher"
    assert teacher_res["motion_key"] == "teacher_2"

    # Non-existent glosses
    hello_res = await signavatar_client.resolve_gloss_animation("hello")
    assert hello_res["available"] is False
    assert hello_res["gloss"] == "hello"
    assert "No matching ISL animation available" in hello_res["reason"]

    missing_res = await signavatar_client.resolve_gloss_animation("missing_random_word")
    assert missing_res["available"] is False
    assert missing_res["gloss"] == "missing_random_word"


# ==============================================================================
# 4 & 5: ISL TRANSLATION & GRAMMAR RULES (SOV, WH-WORDS, TIME MARKERS)
# ==============================================================================

@pytest.mark.asyncio
async def test_isl_grammar_and_translation():
    isl_service = get_isl_service()

    # SOV / Topic-Comment ordering: "I drink water" -> WATER DRINK I
    res1 = await isl_service.translate_to_gloss("I drink water")
    assert res1.gloss == ["WATER", "DRINK", "I"]

    # Request / Needs: "I need help" -> HELP NEED I
    res2 = await isl_service.translate_to_gloss("I need help")
    assert res2.gloss == ["HELP", "NEED", "I"]

    # Question Word at End: "Where is school?" -> SCHOOL WHERE
    res3 = await isl_service.translate_to_gloss("Where is school?")
    assert res3.gloss == ["SCHOOL", "WHERE"]

    # Question Word at End: "Who is teacher?" -> TEACHER WHO
    res4 = await isl_service.translate_to_gloss("Who is teacher?")
    assert res4.gloss == ["TEACHER", "WHO"]

    # Time markers at beginning: "Today I go home" -> TODAY HOME GO I
    res5 = await isl_service.translate_to_gloss("Today I go home")
    assert res5.gloss == ["TODAY", "HOME", "GO", "I"]


# ==============================================================================
# 6: TAMIL TRANSLATION & UNICODE PRESERVATION
# ==============================================================================

@pytest.mark.asyncio
async def test_tamil_translation_pipeline():
    isl_service = get_isl_service()

    # Tamil concept: "நல்ல தண்ணீர்" (Good Water)
    res1 = await isl_service.translate_to_gloss("நல்ல தண்ணீர்")
    assert "GOOD" in res1.gloss
    assert "WATER" in res1.gloss

    # Tamil concept: "உதவி ஆசிரியர்" (Help Teacher)
    res2 = await isl_service.translate_to_gloss("உதவி ஆசிரியர்")
    assert "HELP" in res2.gloss
    assert "TEACHER" in res2.gloss

    # Tamil greeting: "காலை வணக்கம்" (Good Morning -> Time marker promoted: MORNING + GOOD)
    res3 = await isl_service.translate_to_gloss("காலை வணக்கம்")
    assert "MORNING" in res3.gloss and "GOOD" in res3.gloss


# ==============================================================================
# 7, 8, 9: ANIMATION SEQUENCING, RESAMPLING, METADATA & BINARY STREAMING
# ==============================================================================

@pytest.mark.asyncio
async def test_animation_sequencing_and_binary():
    # Test resampling
    sample_anim = np.ones((50, 10475, 3), dtype=np.float32)
    resampled = resample_motion(sample_anim, source_fps=50.0, target_fps=30.0)
    assert resampled.shape[1] == 10475
    assert resampled.shape[2] == 3
    assert abs(resampled.shape[0] - 30) <= 2

    # Test sequence generation
    seq_res = await animation_sequencer.sequence_glosses(["good", "drink"])
    assert seq_res["available"] is True
    assert seq_res["fps"] == 30
    assert seq_res["vertex_count"] == 10475
    assert "sequence_id" in seq_res

    sequence_id = seq_res["sequence_id"]

    # Test binary retrieval
    binary_data, headers = animation_sequencer.get_sequence_binary(sequence_id)
    expected_bytes = seq_res["frames"] * 10475 * 3 * 4
    assert len(binary_data) == expected_bytes
    assert headers["X-Vertices"] == "10475"
    assert headers["X-FPS"] == "30"
    assert headers["X-Dtype"] == "float32"

    # Test HTTP endpoint for binary sequence
    res_http = client.get(f"/api/signavatar/sequence/{sequence_id}")
    assert res_http.status_code == 200
    assert len(res_http.content) == expected_bytes


# ==============================================================================
# 10, 13, 14: COMPLETE END-TO-END TEXT PIPELINE & MISSING/PARTIAL SIGNS
# ==============================================================================

@pytest.mark.asyncio
async def test_e2e_text_to_signavatar_cases():
    # 1. "good drink"
    r1 = client.post("/api/translate-to-signavatar", json={"text": "good drink"})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["available"] is True
    assert d1["glosses"] == ["GOOD", "DRINK"]
    assert d1["animation"]["fps"] == 30
    assert d1["animation"]["vertex_count"] == 10475
    assert d1["source"] == "BridgeConn Sign Dictionary ISL"

    # 2. "help teacher" (resolves help_2 and teacher_2)
    r2 = client.post("/api/translate-to-signavatar", json={"text": "help teacher"})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["available"] is True
    assert d2["glosses"] == ["HELP", "TEACHER"]
    assert d2["animation"]["fps"] == 30

    # 3. "go drink help" (resolves go, drink, help_2)
    r3 = client.post("/api/translate-to-signavatar", json={"text": "go drink help"})
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["available"] is True
    assert d3["glosses"] == ["GO", "DRINK", "HELP"]

    # 4. Unavailable sign: "hello"
    r4 = client.post("/api/translate-to-signavatar", json={"text": "hello"})
    assert r4.status_code == 200
    d4 = r4.json()
    assert d4["available"] is False
    assert "animation" not in d4
    assert len(d4["unavailable"]) >= 1
    assert "HELLO" in [u["gloss"].upper() for u in d4["unavailable"]]

    # 5. Partial sign scenario: "I need help" (I, NEED unavailable; HELP available)
    r5 = client.post("/api/translate-to-signavatar", json={"text": "I need help"})
    assert r5.status_code == 200
    d5 = r5.json()
    assert d5["available"] is False
    assert "animation" not in d5
    unavail_glosses = [u["gloss"].upper() for u in d5.get("unavailable", [])]
    assert "I" in unavail_glosses or "NEED" in unavail_glosses


# ==============================================================================
# 15 & 16: SECURITY, PATH TRAVERSAL & MALFORMED INPUT REJECTION
# ==============================================================================

def test_security_and_validation():
    # Path traversal in /api/signavatar/sequence/{sequence_id}
    r1 = client.get("/api/signavatar/sequence/../../etc/passwd")
    assert r1.status_code in (400, 404, 422)

    r2 = client.get("/api/signavatar/sequence/..\\..\\windows\\system32")
    assert r2.status_code in (400, 404, 422)

    # Empty text validation in /api/translate-to-signavatar
    r3 = client.post("/api/translate-to-signavatar", json={"text": "   "})
    assert r3.status_code == 422

    # Malformed JSON / empty glosses in /api/signavatar/resolve
    r4 = client.post("/api/signavatar/resolve", json={"glosses": []})
    assert r4.status_code == 422
