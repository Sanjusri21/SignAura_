"""
Isolated Coordinate Adapter for iSign World Body Landmarks.
Extracts uncalibrated relative 3D joint directions from POSE_WORLD_LANDMARKS,
and anchors them to canonical fixed-length SMPL-X reference bones.
Does NOT attempt metric reconstruction or assume units are meters/cm/mm.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import numpy as np
import torch


# MediaPipe BlazePose landmark indices
MP_NOSE = 0
MP_LEFT_SHOULDER = 11
MP_RIGHT_SHOULDER = 12
MP_LEFT_ELBOW = 13
MP_RIGHT_ELBOW = 14
MP_LEFT_WRIST = 15
MP_RIGHT_WRIST = 16
MP_LEFT_HIP = 23
MP_RIGHT_HIP = 24
MP_LEFT_KNEE = 25
MP_RIGHT_KNEE = 26
MP_LEFT_ANKLE = 27
MP_RIGHT_ANKLE = 28


def safe_normalize(v: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    """Normalize vectors along the last axis safely."""
    norm = np.linalg.norm(v, axis=-1, keepdims=True)
    norm = np.where(norm < eps, eps, norm)
    return v / norm


@dataclass
class CanonicalBoneLengths:
    shoulder_width: float
    hip_width: float
    torso_height: float
    left_upper_arm: float
    left_forearm: float
    right_upper_arm: float
    right_forearm: float
    left_thigh: float
    left_shin: float
    right_thigh: float
    right_shin: float


class ISignCoordinateAdapter:
    """
    Computes canonical reference bone lengths from the neutral SMPL-X template,
    and projects observed monocular iSign joint directions onto these fixed lengths.
    """

    def __init__(self, human_model_path: Optional[str | Path] = None):
        if human_model_path is None:
            # Locate human_model_files in SignAvatars
            base = Path(__file__).resolve().parent.parent / "common" / "utils" / "human_model_files"
            human_model_path = base
        else:
            human_model_path = Path(human_model_path)

        smplx_npz = human_model_path / "smplx" / "SMPLX_NEUTRAL.npz"
        if not smplx_npz.exists():
            raise FileNotFoundError(f"SMPL-X neutral template not found at: {smplx_npz}")

        data = np.load(str(smplx_npz), allow_pickle=True)
        v_template = data["v_template"]  # (10475, 3)
        j_regressor = data["J_regressor"] # (55, 10475) or sparse matrix
        
        if hasattr(j_regressor, "toarray"):
            J_reg = j_regressor.toarray()
        elif hasattr(j_regressor, "shape") and len(j_regressor.shape) == 2:
            J_reg = np.array(j_regressor)
        elif hasattr(j_regressor, "dtype") and j_regressor.dtype == object:
            J_reg = j_regressor.item().toarray()
        else:
            J_reg = np.array(j_regressor)

        # Precompute rest joints J_rest [55, 3]
        self.J_rest = np.matmul(J_reg, v_template)

        # SMPL-X joint indices:
        # 0: pelvis, 1: L_hip, 2: R_hip, 3: spine1, 6: spine2, 9: spine3, 12: neck, 15: head
        # 16: L_shoulder, 17: R_shoulder, 18: L_elbow, 19: R_elbow, 20: L_wrist, 21: R_wrist
        # 4: L_knee, 5: R_knee, 7: L_ankle, 8: R_ankle
        J = self.J_rest
        self.canonical = CanonicalBoneLengths(
            shoulder_width=float(np.linalg.norm(J[16] - J[17])),
            hip_width=float(np.linalg.norm(J[1] - J[2])),
            torso_height=float(np.linalg.norm(J[12] - J[0])),
            left_upper_arm=float(np.linalg.norm(J[18] - J[16])),
            left_forearm=float(np.linalg.norm(J[20] - J[18])),
            right_upper_arm=float(np.linalg.norm(J[19] - J[17])),
            right_forearm=float(np.linalg.norm(J[21] - J[19])),
            left_thigh=float(np.linalg.norm(J[4] - J[1])),
            left_shin=float(np.linalg.norm(J[7] - J[4])),
            right_thigh=float(np.linalg.norm(J[5] - J[2])),
            right_shin=float(np.linalg.norm(J[8] - J[5])),
        )

    def extract_body_directions(self, world_body: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Extracts unit direction vectors for all body segments from POSE_WORLD_LANDMARKS.
        Input: (T, 33, 3)
        Output: dict of unit direction arrays (T, 3).
        """
        # Convert MediaPipe camera coordinate frame (+Y down, +Z away)
        # to SMPL-X standard 3D coordinate frame (+Y up, +Z towards viewer).
        # iSign landmarks store X and Y in pixel grid coords (scaled by dimensions 300),
        # whereas Z is unscaled in physical meters (dimensions.depth == 0).
        # We restore 3D metric isotropy by normalizing X and Y by 300.0.
        scale = 300.0
        wb = world_body.copy()
        wb[:, :, 0] = wb[:, :, 0] / scale
        wb[:, :, 1] = -wb[:, :, 1] / scale
        wb[:, :, 2] = -wb[:, :, 2]

        T = wb.shape[0]

        # Key joint trajectories
        sh_l = wb[:, MP_LEFT_SHOULDER, :]
        sh_r = wb[:, MP_RIGHT_SHOULDER, :]
        el_l = wb[:, MP_LEFT_ELBOW, :]
        el_r = wb[:, MP_RIGHT_ELBOW, :]
        wr_l = wb[:, MP_LEFT_WRIST, :]
        wr_r = wb[:, MP_RIGHT_WRIST, :]
        hip_l = wb[:, MP_LEFT_HIP, :]
        hip_r = wb[:, MP_RIGHT_HIP, :]
        nose = wb[:, MP_NOSE, :]

        # Midpoints
        sh_mid = (sh_l + sh_r) * 0.5
        hip_mid = (hip_l + hip_r) * 0.5

        # Directions
        dir_torso_up = safe_normalize(sh_mid - hip_mid)
        dir_shoulder_across = safe_normalize(sh_l - sh_r)
        dir_hip_across = safe_normalize(hip_l - hip_r)

        # Torso normal (facing direction) via right-handed cross product
        dir_torso_normal = safe_normalize(np.cross(dir_shoulder_across, dir_torso_up))
        # Re-orthonormalize across to ensure perfect orthogonal frame
        dir_shoulder_across = safe_normalize(np.cross(dir_torso_up, dir_torso_normal))

        # Upper arm and forearm directions
        dir_l_upper_arm = safe_normalize(el_l - sh_l)
        dir_l_forearm = safe_normalize(wr_l - el_l)

        dir_r_upper_arm = safe_normalize(el_r - sh_r)
        dir_r_forearm = safe_normalize(wr_r - el_r)

        # Neck / head direction
        dir_neck = safe_normalize(nose - sh_mid)

        return {
            "torso_up": dir_torso_up,
            "shoulder_across": dir_shoulder_across,
            "hip_across": dir_hip_across,
            "torso_normal": dir_torso_normal,
            "left_upper_arm": dir_l_upper_arm,
            "left_forearm": dir_l_forearm,
            "right_upper_arm": dir_r_upper_arm,
            "right_forearm": dir_r_forearm,
            "neck": dir_neck,
            "hip_mid": hip_mid,
            "shoulder_mid": sh_mid,
        }

    def build_canonical_bone_vectors(self, directions: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """
        Scales unit directions by SMPL-X fixed canonical lengths.
        Guarantees that bone lengths remain completely rigid across all frames.
        """
        c = self.canonical
        return {
            "vec_left_upper_arm": directions["left_upper_arm"] * c.left_upper_arm,
            "vec_left_forearm": directions["left_forearm"] * c.left_forearm,
            "vec_right_upper_arm": directions["right_upper_arm"] * c.right_upper_arm,
            "vec_right_forearm": directions["right_forearm"] * c.right_forearm,
            "vec_torso": directions["torso_up"] * c.torso_height,
            "vec_shoulder": directions["shoulder_across"] * c.shoulder_width,
            "vec_hip": directions["hip_across"] * c.hip_width,
        }
