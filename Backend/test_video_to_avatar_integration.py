"""
Integration tests for Complete Video-to-Avatar Pipeline (Phase 4).
Tests:
1. Valid short video media processing via execute_video_pipeline
2. Valid audio processing via FFmpeg/Whisper
3. Tamil input speech/text translation and animation resolution
4. Silent media / empty transcript error handling
5. Malformed or nonexistent media error handling
6. Partial and missing gloss sequence handling downstream
7. End-to-end serialized 3D binary payload generation for Three.js playback
"""

import os
import sys
import pytest
import numpy as np
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.main import app
from app.workers.celery_app import execute_video_pipeline
from app.services.translation_animation_service import translation_animation_service
from app.services.animation_sequencer import animation_sequencer

client = TestClient(app)

TEST_VIDEO_PATH = os.path.join(
    BASE_DIR,
    "The Bear and the Bee - US English accent (TheFableCottage.com) [jKi2SvWOCXc].mp4"
)
TEST_AUDIO_PATH = os.path.join(
    BASE_DIR,
    "The Bear and the Bee - US English accent (TheFableCottage.com) [jKi2SvWOCXc]_audio.wav"
)


@pytest.mark.asyncio
async def test_video_pipeline_with_real_media():
    """1. Process real video media through FFmpeg -> Whisper -> NLP -> ISL."""
    if not os.path.exists(TEST_VIDEO_PATH):
        pytest.skip(f"Test video not found: {TEST_VIDEO_PATH}")

    # Process first part of real video file
    result = await execute_video_pipeline(
        video_path=TEST_VIDEO_PATH,
        dialect="standard",
        job_id="test-job-real-video"
    )

    assert result["status"] == "completed"
    assert result["language"] in ("en", "english")
    assert len(result["transcript"]) > 0
    assert result["duration"] > 0
    assert result["language_supported"] is True
    assert len(result["gloss"]) > 0
    assert len(result["tokens"]) > 0


@pytest.mark.asyncio
async def test_audio_pipeline_with_real_audio():
    """2. Process real audio file through transcription and gloss generation."""
    if not os.path.exists(TEST_AUDIO_PATH):
        pytest.skip(f"Test audio not found: {TEST_AUDIO_PATH}")

    result = await execute_video_pipeline(
        video_path=TEST_AUDIO_PATH,
        dialect="standard",
        job_id="test-job-real-audio"
    )

    assert result["status"] == "completed"
    assert len(result["transcript"]) > 0
    assert result["language_supported"] is True


@pytest.mark.asyncio
async def test_tamil_video_pipeline_translation():
    """3. Process Tamil speech/text transcript through Tamil NLP -> ISL -> 3D motion."""
    # Simulate Tamil audio transcript detection
    result = await execute_video_pipeline(
        video_path=TEST_VIDEO_PATH if os.path.exists(TEST_VIDEO_PATH) else "dummy.mp4",
        dialect="standard",
        job_id="test-job-tamil",
        transcript_override="வணக்கம் உதவி ஆசிரியர்"
    )

    assert result["status"] == "completed"
    assert result["language_supported"] is True
    # Verify gloss tokens produced for Tamil input
    gloss_list = result["gloss"] if isinstance(result["gloss"], list) else result["gloss"].split()
    assert "TEACHER" in [g.upper() for g in gloss_list]
    assert "HELP" in [g.upper() for g in gloss_list]

    # Verify downstream animation resolves for the Tamil concepts
    seq_res = await translation_animation_service.translate_and_sequence("உதவி ஆசிரியர்")
    assert seq_res["available"] is True
    assert "animation" in seq_res
    assert seq_res["animation"]["vertex_count"] == 10475


@pytest.mark.asyncio
async def test_silent_media_handling():
    """4. Empty transcription / silent media raises descriptive error."""
    with patch("app.services.video.ffmpeg_processor.ffmpeg_processor.extract_audio", new=AsyncMock(return_value="silent.wav")):
        with patch("app.services.speech.whisper_service.whisper_service.transcribe", new=AsyncMock(return_value={"text": "   ", "language": "en", "duration": 5.0})):
            with pytest.raises(RuntimeError, match="No speech was detected"):
                await execute_video_pipeline(
                    video_path="silent_video.mp4",
                    job_id="test-silent"
                )


@pytest.mark.asyncio
async def test_malformed_media_handling():
    """5. Malformed or nonexistent media path handling."""
    with pytest.raises(Exception):
        await execute_video_pipeline(
            video_path="nonexistent_corrupted_file_12345.mp4",
            job_id="test-malformed"
        )


@pytest.mark.asyncio
async def test_downstream_animation_resolution_from_transcript():
    """6. Ensure transcript words map to authentic SMPL-X sequence without fake substitutions."""
    # Sentence with known authentic signs: "good drink help teacher"
    transcript = "good drink help teacher"
    anim_res = await translation_animation_service.translate_and_sequence(transcript)

    assert anim_res["available"] is True
    anim = anim_res["animation"]
    assert anim["fps"] == 30
    assert anim["vertex_count"] == 10475
    assert anim["frames"] > 0

    # Fetch binary stream from the generated URL
    r_bin = client.get(anim["animation_url"])
    assert r_bin.status_code == 200

    # Validate Three.js compatibility: Float32, finite, correct byte length
    expected_bytes = anim["frames"] * 10475 * 3 * 4
    assert len(r_bin.content) == expected_bytes
    arr = np.frombuffer(r_bin.content, dtype=np.float32)
    assert np.isfinite(arr).all()


@pytest.mark.asyncio
async def test_partially_available_transcript_downstream():
    """7. Transcript containing mixed available and unavailable words."""
    transcript = "drink soda"
    anim_res = await translation_animation_service.translate_and_sequence(transcript)

    assert anim_res["available"] is False
    assert "animation" not in anim_res
    assert "unavailable" in anim_res
    assert "SODA" in [u["gloss"].upper() for u in anim_res["unavailable"]]
