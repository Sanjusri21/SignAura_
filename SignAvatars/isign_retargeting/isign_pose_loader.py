"""
Isolated pose loader for genuine iSign .pose files.
Extracts 33 Body, 21 Left Hand, 21 Right Hand, and 33 World Body landmarks with confidences.
Does NOT fabricate or substitute any landmark data.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
from pose_format import Pose


@dataclass
class ISignPoseData:
    fps: float
    frames: int
    body: np.ndarray        # (T, 33, 3)
    left_hand: np.ndarray   # (T, 21, 3)
    right_hand: np.ndarray  # (T, 21, 3)
    world_body: np.ndarray  # (T, 33, 3)
    conf_body: np.ndarray        # (T, 33)
    conf_left_hand: np.ndarray   # (T, 21)
    conf_right_hand: np.ndarray  # (T, 21)
    conf_world_body: np.ndarray  # (T, 33)


def load_isign_pose(pose_path: str | Path) -> ISignPoseData:
    """
    Loads and extracts genuine components from an official iSign .pose file.
    Topology:
      - POSE_LANDMARKS: 0..32 (33)
      - FACE_LANDMARKS: 33..500 (468) [Ignored for body/hand retargeting]
      - LEFT_HAND_LANDMARKS: 501..521 (21)
      - RIGHT_HAND_LANDMARKS: 522..542 (21)
      - POSE_WORLD_LANDMARKS: 543..575 (33)
    """
    path = Path(pose_path)
    if not path.exists():
        raise FileNotFoundError(f"iSign pose file not found at: {path}")

    raw_bytes = path.read_bytes()
    pose = Pose.read(raw_bytes)

    fps = float(pose.body.fps) if hasattr(pose.body, "fps") and pose.body.fps else 25.0

    raw_data = pose.body.data
    if hasattr(raw_data, "filled"):
        arr = raw_data.filled(0.0)
    elif hasattr(raw_data, "numpy"):
        arr = raw_data.numpy()
    else:
        arr = np.array(raw_data, dtype=np.float32)

    conf_raw = pose.body.confidence
    if hasattr(conf_raw, "filled"):
        conf = conf_raw.filled(0.0)
    elif hasattr(conf_raw, "numpy"):
        conf = conf_raw.numpy()
    else:
        conf = np.array(conf_raw, dtype=np.float32)

    T, P, L, D = arr.shape
    if P != 1 or L != 576 or D < 3:
        raise ValueError(f"Unexpected iSign tensor shape: {arr.shape}. Expected (T, 1, 576, >=3).")

    # Extract slices
    body = arr[:, 0, 0:33, :3].astype(np.float32)
    left_hand = arr[:, 0, 501:522, :3].astype(np.float32)
    right_hand = arr[:, 0, 522:543, :3].astype(np.float32)
    world_body = arr[:, 0, 543:576, :3].astype(np.float32)

    conf_body = conf[:, 0, 0:33].astype(np.float32)
    conf_lh = conf[:, 0, 501:522].astype(np.float32)
    conf_rh = conf[:, 0, 522:543].astype(np.float32)
    conf_wb = conf[:, 0, 543:576].astype(np.float32)

    return ISignPoseData(
        fps=fps,
        frames=T,
        body=body,
        left_hand=left_hand,
        right_hand=right_hand,
        world_body=world_body,
        conf_body=conf_body,
        conf_left_hand=conf_lh,
        conf_right_hand=conf_rh,
        conf_world_body=conf_wb,
    )
