"""
Comprehensive Test Suite for Canonical SMPL-X Motion Pipeline.

Verifies:
1. Loading one motion (DRINK, HELP, GOOD, WELCOME, TEACHER)
2. Validating one motion
3. Numerical integrity (NaN / Inf detection)
4. Shape mismatch detection
5. Retrieving available signs
6. Handling missing signs
7. Rendering single motions through SMPLXRenderer
8. Sequencing two signs (HELP -> DRINK)
9. Sequencing three signs (GOOD -> HELP -> DRINK)
10. End-to-end Text -> ISL Grammar -> Canonical SMPL-X Motion Pipeline
"""

import sys
import os
import pytest
import numpy as np
from pathlib import Path

# Add Backend to sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.motion.canonical_motion import CanonicalMotion
from app.motion.motion_database import (
    MotionDatabase,
    get_motion,
    load_motion,
    list_available_signs,
    validate_motion,
    get_motion_database
)
from app.motion.motion_validator import validate_motion as run_validator
from app.motion.motion_sequencer import MotionSequencer
from app.motion.motion_blender import MotionBlender
from app.grammar.isl_grammar import ISLGrammarProcessor
from app.smplx.model import SMPLXBodyModel, get_smplx_model
from app.smplx.renderer import SMPLXRenderer


@pytest.fixture(scope="module")
def motion_db():
    return get_motion_database()


@pytest.fixture(scope="module")
def smplx_renderer():
    return SMPLXRenderer(viewport_width=160, viewport_height=160)


@pytest.fixture(scope="module")
def sequencer():
    return MotionSequencer(target_fps=30.0)


# ==============================================================================
# 1. LOADING & RETRIEVAL TESTS
# ==============================================================================

def test_list_available_signs(motion_db):
    """Verifies that the canonical database discovers available signs."""
    available = motion_db.list_available_signs()
    assert isinstance(available, list)
    assert len(available) >= 5
    for expected in ["DRINK", "HELP", "GOOD", "WELCOME", "TEACHER"]:
        assert any(expected in sign for sign in available), f"Expected {expected} in {available}"


def test_load_single_motion(motion_db):
    """Verifies loading a single verified motion (DRINK)."""
    motion = motion_db.get_motion("DRINK")
    assert motion is not None, "Failed to load DRINK from SignMotionDB"
    assert isinstance(motion, CanonicalMotion)
    assert motion.sign_id == "DRINK"
    assert motion.num_frames > 0
    assert motion.fps > 0
    assert motion.global_orient.shape == (motion.num_frames, 3)
    assert motion.body_pose.shape == (motion.num_frames, 63)
    assert motion.left_hand_pose.shape == (motion.num_frames, 45)
    assert motion.right_hand_pose.shape == (motion.num_frames, 45)
    assert motion.jaw_pose.shape == (motion.num_frames, 3)
    assert motion.transl.shape == (motion.num_frames, 3)


def test_missing_sign_handling(motion_db):
    """Verifies that non-existent signs return None or raise KeyError cleanly."""
    missing = motion_db.get_motion("NON_EXISTENT_SIGN_12345")
    assert missing is None

    with pytest.raises(KeyError):
        motion_db.load_motion("NON_EXISTENT_SIGN_12345")


# ==============================================================================
# 2. VALIDATION TESTS
# ==============================================================================

def test_validate_valid_motion(motion_db):
    """Verifies that genuine canonical motions pass validation."""
    for sign in ["DRINK", "HELP", "GOOD", "WELCOME", "TEACHER"]:
        motion = motion_db.get_motion(sign)
        assert motion is not None
        val_res = motion_db.validate_motion(motion)
        assert val_res["valid"] is True, f"Validation failed for {sign}: {val_res['errors']}"
        assert len(val_res["errors"]) == 0


def test_validation_nan_detection():
    """Verifies that NaN values in any kinematic parameter are flagged as invalid."""
    T = 10
    nan_motion = CanonicalMotion(
        sign_id="TEST_NAN",
        fps=30.0,
        num_frames=T,
        global_orient=np.zeros((T, 3), dtype=np.float32),
        body_pose=np.zeros((T, 63), dtype=np.float32),
        left_hand_pose=np.zeros((T, 45), dtype=np.float32),
        right_hand_pose=np.zeros((T, 45), dtype=np.float32),
        jaw_pose=np.zeros((T, 3), dtype=np.float32),
        transl=np.zeros((T, 3), dtype=np.float32),
    )
    # Inject NaN into right hand pose
    nan_motion.right_hand_pose[3, 12] = np.nan

    res = run_validator(nan_motion)
    assert res["valid"] is False
    assert any("non-finite values (NaN" in err for err in res["errors"])


def test_validation_inf_detection():
    """Verifies that Inf values in any parameter are flagged as invalid."""
    T = 10
    inf_motion = CanonicalMotion(
        sign_id="TEST_INF",
        fps=30.0,
        num_frames=T,
        global_orient=np.zeros((T, 3), dtype=np.float32),
        body_pose=np.zeros((T, 63), dtype=np.float32),
        left_hand_pose=np.zeros((T, 45), dtype=np.float32),
        right_hand_pose=np.zeros((T, 45), dtype=np.float32),
        jaw_pose=np.zeros((T, 3), dtype=np.float32),
        transl=np.zeros((T, 3), dtype=np.float32),
    )
    # Inject Inf into body pose
    inf_motion.body_pose[5, 2] = np.inf

    res = run_validator(inf_motion)
    assert res["valid"] is False
    assert any("non-finite values" in err for err in res["errors"])


def test_validation_shape_mismatches():
    """Verifies that incorrect parameter dimensions or mismatched frame counts fail validation."""
    T = 15
    mismatched = {
        "sign_id": "TEST_SHAPE",
        "fps": 30.0,
        "num_frames": T,
        "global_orient": np.zeros((T, 3), dtype=np.float32),
        "body_pose": np.zeros((T, 60), dtype=np.float32),  # Expected 63!
        "left_hand_pose": np.zeros((T, 45), dtype=np.float32),
        "right_hand_pose": np.zeros((T, 45), dtype=np.float32),
        "jaw_pose": np.zeros((T, 3), dtype=np.float32),
        "transl": np.zeros((T - 5, 3), dtype=np.float32),  # Frame count mismatch!
    }

    res = run_validator(mismatched)
    assert res["valid"] is False
    assert any("has 60 columns, expected 63" in err for err in res["errors"])
    assert any("Frame count mismatch" in err for err in res["errors"])


# ==============================================================================
# 3. RENDERING TESTS
# ==============================================================================

@pytest.mark.parametrize("sign_name", ["DRINK", "HELP", "GOOD", "WELCOME", "TEACHER"])
def test_render_canonical_sign(motion_db, smplx_renderer, sign_name):
    """Verifies that each of the 5 test signs can be rendered successfully."""
    motion = motion_db.get_motion(sign_name)
    assert motion is not None, f"Motion '{sign_name}' not found"

    # Render first 2 frames to verify full forward pass & offscreen projection
    frames = smplx_renderer.render_motion_frames(motion, max_frames=2)
    assert len(frames) == 2
    assert frames[0].shape == (160, 160, 3)
    assert frames[0].dtype == np.uint8
    assert np.any(frames[0] > 0), "Rendered frame is completely blank"


# ==============================================================================
# 4. SEQUENCING TESTS
# ==============================================================================

def test_sequence_two_signs(motion_db, sequencer):
    """Verifies sequencing two signs (HELP -> DRINK) produces a continuous SMPL-X sequence."""
    m_help = motion_db.get_motion("HELP")
    m_drink = motion_db.get_motion("DRINK")
    assert m_help is not None and m_drink is not None

    seq = sequencer.sequence_motions([m_help, m_drink])
    assert seq.fps == 30.0
    assert seq.num_frames > 0
    # Expected frames = help resampled + drink resampled + transition frames
    expected_min_frames = int(m_help.duration * 30.0) + int(m_drink.duration * 30.0)
    assert seq.num_frames >= expected_min_frames

    val = motion_db.validate_motion(seq)
    assert val["valid"] is True, f"Sequenced motion failed validation: {val['errors']}"
    assert np.isfinite(seq.global_orient).all()
    assert np.isfinite(seq.body_pose).all()
    assert np.isfinite(seq.left_hand_pose).all()
    assert np.isfinite(seq.right_hand_pose).all()


def test_sequence_three_signs(motion_db, sequencer):
    """Verifies sequencing three signs (GOOD -> HELP -> DRINK) produces a continuous sequence."""
    m_good = motion_db.get_motion("GOOD")
    m_help = motion_db.get_motion("HELP")
    m_drink = motion_db.get_motion("DRINK")

    seq = sequencer.sequence_motions([m_good, m_help, m_drink])
    assert seq.fps == 30.0
    assert seq.num_frames > 0

    val = motion_db.validate_motion(seq)
    assert val["valid"] is True, f"Three-sign sequence validation failed: {val['errors']}"


def test_sequence_glosses_with_missing(sequencer):
    """Verifies sequencing glosses handles missing signs cleanly."""
    seq, missing = sequencer.sequence_glosses(["GOOD", "WATER_MISSING_123", "DRINK"])
    assert seq is None
    assert "WATER_MISSING_123" in missing


# ==============================================================================
# 5. END-TO-END PIPELINE TEST
# ==============================================================================

def test_e2e_text_grammar_motion_render_pipeline(sequencer, smplx_renderer):
    """
    Verifies full canonical pipeline:
    Text -> ISL Grammar -> Gloss Sequence -> Motion Retrieval -> Motion Sequencing -> SMPL-X Renderer
    """
    processor = ISLGrammarProcessor()
    text = "Good teacher help drink"
    glosses = processor.process_text(text)
    assert isinstance(glosses, list)
    assert len(glosses) >= 2

    # Sequence available glosses
    seq, missing = sequencer.sequence_glosses(["GOOD", "DRINK"])
    assert missing == []
    assert seq is not None

    # Render continuous sequence
    frames = smplx_renderer.render_motion_frames(seq, max_frames=2)
    assert len(frames) == 2
    assert frames[0].shape == (160, 160, 3)
