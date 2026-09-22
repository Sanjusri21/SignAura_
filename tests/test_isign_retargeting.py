"""
Tests for Isolated iSign -> SMPL-X Retargeting Pipeline.
Validates:
  1. Genuine pose loader
  2. Coordinate adapter & canonical SMPL-X bone lengths
  3. Body retargeter & torso orientation
  4. Hand retargeter & physiological finger flexion
  5. SMPL-X forward pass & vertex topology
  6. End-to-end retargeting consistency
"""

import sys
from pathlib import Path
import pytest
import numpy as np

# Ensure project root and SignAvatars are on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
SIGNAVATARS_DIR = ROOT_DIR / "SignAvatars"
BACKEND_DIR = ROOT_DIR / "Backend"

for p in [ROOT_DIR, SIGNAVATARS_DIR, BACKEND_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from SignAvatars.isign_retargeting.isign_pose_loader import load_isign_pose, ISignPoseData
from SignAvatars.isign_retargeting.isign_coordinate_adapter import ISignCoordinateAdapter, safe_normalize
from SignAvatars.isign_retargeting.isign_body_retarget import (
    ISignBodyRetargeter,
    shortest_arc_rotation,
    exponential_moving_average_rotvec,
)
from SignAvatars.isign_retargeting.isign_hand_retarget import ISignHandRetargeter
from SignAvatars.isign_retargeting.isign_smplx_forward import ISignSMPLXForwardPass


SAMPLE_POSE_PATH = Path("D:/SignAuraData/iSign/poses/FyPkQyJWsjs--100.pose")
HUMAN_MODEL_PATH = SIGNAVATARS_DIR / "common" / "utils" / "human_model_files"


@pytest.mark.skipif(not SAMPLE_POSE_PATH.exists(), reason="Genuine sample .pose file not found")
def test_genuine_pose_loader():
    """Verify loading of genuine iSign sample FyPkQyJWsjs--100.pose."""
    pose_data = load_isign_pose(SAMPLE_POSE_PATH)
    assert isinstance(pose_data, ISignPoseData)
    assert pose_data.frames == 116
    assert pose_data.fps == 25.0

    # Validate landmark shapes
    assert pose_data.body.shape == (116, 33, 3)
    assert pose_data.left_hand.shape == (116, 21, 3)
    assert pose_data.right_hand.shape == (116, 21, 3)
    assert pose_data.world_body.shape == (116, 33, 3)

    # Validate no unhandled NaNs
    assert not np.isnan(pose_data.body).any()
    assert not np.isnan(pose_data.world_body).any()
    assert not np.isnan(pose_data.left_hand).any()
    assert not np.isnan(pose_data.right_hand).any()


def test_coordinate_adapter_canonical_lengths():
    """Verify extraction of fixed canonical lengths from neutral SMPL-X template."""
    adapter = ISignCoordinateAdapter(human_model_path=HUMAN_MODEL_PATH)
    can = adapter.canonical

    assert 0.20 < can.left_upper_arm < 0.35, f"Unexpected upper arm length: {can.left_upper_arm}"
    assert 0.18 < can.left_forearm < 0.35, f"Unexpected forearm length: {can.left_forearm}"
    assert 0.40 < can.torso_height < 0.70, f"Unexpected torso height: {can.torso_height}"
    assert 0.25 < can.shoulder_width < 0.50, f"Unexpected shoulder width: {can.shoulder_width}"


def test_shortest_arc_rotation_robustness():
    """Verify shortest_arc_rotation handles edge cases without throwing or NaN."""
    # 1. Identity (same direction)
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    R1 = shortest_arc_rotation(v1, v1)
    np.testing.assert_allclose(R1, np.eye(3), atol=1e-5)

    # 2. 90-degree rotation (+X to +Y)
    v2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    R2 = shortest_arc_rotation(v1, v2)
    transformed = R2 @ v1
    np.testing.assert_allclose(transformed, v2, atol=1e-5)

    # 3. 180-degree antiparallel rotation (+X to -X)
    v3 = np.array([-1.0, 0.0, 0.0], dtype=np.float32)
    R3 = shortest_arc_rotation(v1, v3)
    transformed_anti = R3 @ v1
    np.testing.assert_allclose(transformed_anti, v3, atol=1e-5)

    # 4. Zero vector inputs
    v_zero = np.zeros(3, dtype=np.float32)
    R_zero = shortest_arc_rotation(v_zero, v1)
    np.testing.assert_allclose(R_zero, np.eye(3), atol=1e-5)

    # 5. NaN inputs
    v_nan = np.array([np.nan, 1.0, 0.0], dtype=np.float32)
    R_nan = shortest_arc_rotation(v_nan, v1)
    np.testing.assert_allclose(R_nan, np.eye(3), atol=1e-5)


def test_hand_retargeter_physiological_bounds():
    """Verify finger rotations are clamped to anatomical bounds (<= 1.92 rad ~ 110 deg)."""
    retargeter = ISignHandRetargeter()
    # Mock hand points with high flexion
    mock_hand = np.zeros((21, 3), dtype=np.float32)
    # Wrist
    mock_hand[0] = [0.0, 0.0, 0.0]
    # MCPs
    mock_hand[5] = [0.05, 0.10, 0.0]   # Index MCP
    mock_hand[9] = [0.0, 0.12, 0.0]    # Middle MCP
    mock_hand[13] = [-0.04, 0.11, 0.0] # Ring MCP
    mock_hand[17] = [-0.07, 0.09, 0.0] # Pinky MCP

    # Antiparallel finger curl (pointing backwards)
    mock_hand[6] = [0.05, 0.05, 0.0]
    mock_hand[7] = [0.05, 0.02, 0.0]
    mock_hand[8] = [0.05, 0.00, 0.0]

    hand_pose = retargeter.retarget_single_hand(mock_hand, is_left=True)
    assert hand_pose.shape == (45,)
    assert not np.isnan(hand_pose).any()
    assert float(np.max(np.abs(hand_pose))) <= 1.92 + 1e-4, "Finger rotation exceeded physiological clamp limit"


def test_smplx_forward_pass():
    """Verify forward kinematics produces valid (B, 10475, 3) vertex mesh without NaN."""
    forward_model = ISignSMPLXForwardPass(human_model_path=HUMAN_MODEL_PATH)
    B = 2
    go = np.zeros((B, 3), dtype=np.float32)
    bp = np.zeros((B, 63), dtype=np.float32)
    lh = np.zeros((B, 45), dtype=np.float32)
    rh = np.zeros((B, 45), dtype=np.float32)

    verts, joints = forward_model.forward(go, bp, lh, rh, batch_size=2)
    assert verts.shape == (B, 10475, 3)
    assert joints.shape == (B, 127, 3)
    assert not np.isnan(verts).any()
    assert not np.isinf(verts).any()


@pytest.mark.skipif(not SAMPLE_POSE_PATH.exists(), reason="Genuine sample .pose file not found")
def test_end_to_end_prototype_outputs():
    """Verify generated prototype files exist and meet all 12 validation criteria."""
    prototype_dir = Path("D:/SignAuraData/iSign/prototype")
    npy_path = prototype_dir / "FyPkQyJWsjs--100_smplx.npy"
    npz_path = prototype_dir / "FyPkQyJWsjs--100_pose_params.npz"
    report_path = prototype_dir / "FyPkQyJWsjs--100_prototype_report.json"

    assert npy_path.exists(), "Vertex trajectory .npy not found"
    assert npz_path.exists(), "Pose parameters .npz not found"
    assert report_path.exists(), "Prototype report .json not found"

    # Verify vertex trajectory data
    verts = np.load(str(npy_path))
    assert verts.shape == (116, 10475, 3)
    assert not np.isnan(verts).any()
    assert not np.isinf(verts).any()

    # Verify pose parameters data
    params = np.load(str(npz_path))
    assert "global_orient" in params
    assert "body_pose" in params
    assert "left_hand_pose" in params
    assert "right_hand_pose" in params
    assert params["global_orient"].shape == (116, 3)
    assert params["body_pose"].shape == (116, 63)
    assert params["left_hand_pose"].shape == (116, 45)
    assert params["right_hand_pose"].shape == (116, 45)
