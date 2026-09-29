"""
Canonical SMPL-X Motion Representation.

Defines the standard internal motion data structure for SignAura.
Instead of storing baked vertices (T, 10475, 3), motions are stored exclusively
as canonical SMPL-X kinematic pose parameters.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger("CanonicalMotion")

SMPLX_BODY_POSE_DIM = 63
SMPLX_HAND_POSE_DIM = 45
SMPLX_ORIENT_DIM = 3
SMPLX_TRANSL_DIM = 3
SMPLX_JAW_DIM = 3


@dataclass
class CanonicalMotion:
    """
    Standard internal motion representation using SMPL-X pose parameters.

    Attributes:
        sign_id: Unique string identifier for the sign (e.g. "DRINK", "HELP").
        fps: Playback frame rate (e.g. 20.0, 25.0, 30.0).
        num_frames: Number of temporal frames (T).
        global_orient: Root orientation rotvec (T, 3), float32.
        body_pose: 21 body joint rotvecs (T, 63), float32.
        left_hand_pose: 15 left finger joint rotvecs (T, 45), float32.
        right_hand_pose: 15 right finger joint rotvecs (T, 45), float32.
        jaw_pose: Jaw articulation rotvec (T, 3), float32.
        transl: Global 3D translation (T, 3), float32.
        metadata: Associated contextual metadata (source, description, etc.).
    """

    sign_id: str
    fps: float
    num_frames: int
    global_orient: np.ndarray
    body_pose: np.ndarray
    left_hand_pose: np.ndarray
    right_hand_pose: np.ndarray
    jaw_pose: np.ndarray
    transl: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Enforce float32 and contiguous memory for all kinematic arrays
        self.global_orient = np.ascontiguousarray(self.global_orient, dtype=np.float32)
        self.body_pose = np.ascontiguousarray(self.body_pose, dtype=np.float32)
        self.left_hand_pose = np.ascontiguousarray(self.left_hand_pose, dtype=np.float32)
        self.right_hand_pose = np.ascontiguousarray(self.right_hand_pose, dtype=np.float32)
        self.jaw_pose = np.ascontiguousarray(self.jaw_pose, dtype=np.float32)
        self.transl = np.ascontiguousarray(self.transl, dtype=np.float32)
        self.fps = float(self.fps)
        self.num_frames = int(self.num_frames)

    @property
    def duration(self) -> float:
        """Total duration of motion in seconds."""
        if self.fps <= 0 or self.num_frames <= 0:
            return 0.0
        return self.num_frames / self.fps

    def to_dict(self) -> Dict[str, Any]:
        """Converts to JSON-serializable dictionary (excluding raw large arrays)."""
        return {
            "sign_id": self.sign_id,
            "fps": self.fps,
            "num_frames": self.num_frames,
            "duration_sec": self.duration,
            "shapes": {
                "global_orient": list(self.global_orient.shape),
                "body_pose": list(self.body_pose.shape),
                "left_hand_pose": list(self.left_hand_pose.shape),
                "right_hand_pose": list(self.right_hand_pose.shape),
                "jaw_pose": list(self.jaw_pose.shape),
                "transl": list(self.transl.shape),
            },
            "metadata": self.metadata,
        }

    def save(self, target_dir: Union[str, Path]) -> Tuple[Path, Path]:
        """
        Saves motion to target directory as motion.npz and metadata.json.
        """
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        npz_path = target_dir / "motion.npz"
        json_path = target_dir / "metadata.json"

        np.savez_compressed(
            npz_path,
            sign_id=np.array(self.sign_id),
            fps=np.array(self.fps, dtype=np.float32),
            num_frames=np.array(self.num_frames, dtype=np.int32),
            global_orient=self.global_orient,
            body_pose=self.body_pose,
            left_hand_pose=self.left_hand_pose,
            right_hand_pose=self.right_hand_pose,
            jaw_pose=self.jaw_pose,
            transl=self.transl,
        )

        meta_data = dict(self.metadata)
        meta_data.update({
            "sign_id": self.sign_id,
            "fps": self.fps,
            "num_frames": self.num_frames,
            "duration_sec": self.duration,
            "canonical_format": "SMPL-X Pose Parameters",
        })

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=4)

        logger.info(f"[MOTION DB] Saved {self.sign_id} ({self.num_frames} frames) to {target_dir}")
        return npz_path, json_path

    @classmethod
    def from_npz(
        cls,
        npz_path: Union[str, Path],
        metadata_path: Optional[Union[str, Path]] = None,
        fallback_sign_id: Optional[str] = None
    ) -> CanonicalMotion:
        """
        Loads a CanonicalMotion from an NPZ file and optional metadata JSON.
        Handles both motion.npz and legacy *_smplx_params.npz formats.
        """
        npz_path = Path(npz_path)
        if not npz_path.is_file():
            raise FileNotFoundError(f"Motion NPZ file not found: {npz_path}")

        data = np.load(str(npz_path), allow_pickle=True)

        # 1. Resolve sign_id
        sign_id = fallback_sign_id
        if "sign_id" in data:
            sign_id = str(data["sign_id"].item() if data["sign_id"].ndim == 0 else data["sign_id"][0])
        elif "gloss" in data:
            sign_id = str(data["gloss"].item() if data["gloss"].ndim == 0 else data["gloss"][0])
        if not sign_id:
            sign_id = npz_path.parent.name if npz_path.stem == "motion" else npz_path.stem.replace("_smplx_params", "")

        sign_id = sign_id.upper()

        # 2. Extract kinematic arrays
        if "global_orient" not in data or "body_pose" not in data:
            raise ValueError(f"NPZ file {npz_path} missing required SMPL-X arrays 'global_orient' or 'body_pose'")

        global_orient = data["global_orient"].astype(np.float32)
        body_pose = data["body_pose"].astype(np.float32)
        num_frames = global_orient.shape[0]

        # Left hand pose
        if "left_hand_pose" in data:
            left_hand_pose = data["left_hand_pose"].astype(np.float32)
        else:
            left_hand_pose = np.zeros((num_frames, SMPLX_HAND_POSE_DIM), dtype=np.float32)

        # Right hand pose
        if "right_hand_pose" in data:
            right_hand_pose = data["right_hand_pose"].astype(np.float32)
        else:
            right_hand_pose = np.zeros((num_frames, SMPLX_HAND_POSE_DIM), dtype=np.float32)

        # Jaw pose
        if "jaw_pose" in data:
            jaw_pose = data["jaw_pose"].astype(np.float32)
        else:
            jaw_pose = np.zeros((num_frames, SMPLX_JAW_DIM), dtype=np.float32)

        # Translation
        if "transl" in data:
            transl = data["transl"].astype(np.float32)
        else:
            transl = np.zeros((num_frames, SMPLX_TRANSL_DIM), dtype=np.float32)

        # FPS
        fps = 30.0
        if "fps" in data:
            fps_val = data["fps"]
            fps = float(fps_val.item() if fps_val.ndim == 0 else fps_val[0])

        # Metadata
        metadata: Dict[str, Any] = {}
        if metadata_path is None:
            candidate_meta = npz_path.parent / "metadata.json"
            if candidate_meta.is_file():
                metadata_path = candidate_meta
            else:
                candidate_meta2 = npz_path.with_suffix(".json")
                if candidate_meta2.is_file():
                    metadata_path = candidate_meta2

        if metadata_path and Path(metadata_path).is_file():
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load metadata from {metadata_path}: {e}")

        return cls(
            sign_id=sign_id,
            fps=fps,
            num_frames=num_frames,
            global_orient=global_orient,
            body_pose=body_pose,
            left_hand_pose=left_hand_pose,
            right_hand_pose=right_hand_pose,
            jaw_pose=jaw_pose,
            transl=transl,
            metadata=metadata,
        )

    def resample(self, target_fps: float) -> CanonicalMotion:
        """
        Temporally resamples the motion to target_fps using linear interpolation.
        Returns a new CanonicalMotion instance.
        """
        target_fps = float(target_fps)
        if self.num_frames <= 1 or abs(self.fps - target_fps) < 1e-3:
            return self.clone()

        duration = (self.num_frames - 1) / self.fps
        n_target = max(2, int(round(duration * target_fps)) + 1)

        orig_indices = np.linspace(0.0, float(self.num_frames - 1), n_target, dtype=np.float32)
        idx_floor = np.floor(orig_indices).astype(np.int64)
        idx_ceil = np.minimum(idx_floor + 1, self.num_frames - 1)
        alpha = (orig_indices - idx_floor)[:, None]

        def _interp(arr: np.ndarray) -> np.ndarray:
            return (1.0 - alpha) * arr[idx_floor] + alpha * arr[idx_ceil]

        return CanonicalMotion(
            sign_id=self.sign_id,
            fps=target_fps,
            num_frames=n_target,
            global_orient=_interp(self.global_orient),
            body_pose=_interp(self.body_pose),
            left_hand_pose=_interp(self.left_hand_pose),
            right_hand_pose=_interp(self.right_hand_pose),
            jaw_pose=_interp(self.jaw_pose),
            transl=_interp(self.transl),
            metadata=dict(self.metadata),
        )

    def slice(self, start_frame: int, end_frame: int) -> CanonicalMotion:
        """Returns a time-sliced sub-sequence."""
        start = max(0, start_frame)
        end = min(self.num_frames, end_frame)
        count = max(0, end - start)
        return CanonicalMotion(
            sign_id=self.sign_id,
            fps=self.fps,
            num_frames=count,
            global_orient=self.global_orient[start:end],
            body_pose=self.body_pose[start:end],
            left_hand_pose=self.left_hand_pose[start:end],
            right_hand_pose=self.right_hand_pose[start:end],
            jaw_pose=self.jaw_pose[start:end],
            transl=self.transl[start:end],
            metadata=dict(self.metadata),
        )

    def clone(self) -> CanonicalMotion:
        """Deep copy of the CanonicalMotion."""
        return CanonicalMotion(
            sign_id=self.sign_id,
            fps=self.fps,
            num_frames=self.num_frames,
            global_orient=self.global_orient.copy(),
            body_pose=self.body_pose.copy(),
            left_hand_pose=self.left_hand_pose.copy(),
            right_hand_pose=self.right_hand_pose.copy(),
            jaw_pose=self.jaw_pose.copy(),
            transl=self.transl.copy(),
            metadata=dict(self.metadata),
        )
