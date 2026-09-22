"""
BridgeConn ISL to SMPL-X 3D Animation Retargeting Pipeline.

Mathematically principled retargeting of MediaPipe body landmarks (33)
and hand landmarks (21 left, 21 right) from the BridgeConn ISL dataset
into SMPL-X joint rotations, producing:
  - global_orient (F, 3)
  - body_pose (F, 63)
  - left_hand_pose (F, 45)
  - right_hand_pose (F, 45)
  - transl (F, 3)
and (F, 10475, 3) SMPL-X vertex animation compatible with SignAvatars.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Tuple, Optional

import numpy as np
import torch
from scipy.spatial.transform import Rotation as R

# Ensure base directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Dummy config placeholder for SMPL-X dependencies if needed
try:
    import config
except ImportError:
    import types
    cfg_mod = types.ModuleType("config")
    cfg_mod.cfg = None
    sys.modules["config"] = cfg_mod

from common.utils.smplx import smplx
from common.utils.smplx.smplx.joint_names import JOINT_NAMES

HUMAN_MODEL_PATH = os.path.join(BASE_DIR, "common", "utils", "human_model_files")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("BridgeConnRetarget")


# ==============================================================================
# 1. VECTOR & ROTATION MATHEMATICAL HELPERS
# ==============================================================================

def normalize_vector(v: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    """Normalize 1D or 2D vectors along the last axis safely."""
    norm = np.linalg.norm(v, axis=-1, keepdims=True)
    norm = np.where(norm < eps, eps, norm)
    return v / norm


def rotation_between_vectors(v_from: np.ndarray, v_to: np.ndarray) -> np.ndarray:
    """
    Computes the shortest arc 3x3 rotation matrix that maps unit vector v_from to v_to.
    Uses robust Rodrigues formulation handling parallel and antiparallel cases.
    """
    v_from = normalize_vector(v_from).flatten()
    v_to = normalize_vector(v_to).flatten()

    dot = float(np.dot(v_from, v_to))

    # Identical vectors -> Identity
    if dot > 0.9999999:
        return np.eye(3, dtype=np.float32)

    # Directly opposite vectors -> 180 deg rotation around an orthogonal axis
    if dot < -0.9999999:
        if abs(v_from[0]) < 0.9:
            ortho = np.cross(v_from, np.array([1.0, 0.0, 0.0], dtype=np.float32))
        else:
            ortho = np.cross(v_from, np.array([0.0, 1.0, 0.0], dtype=np.float32))
        ortho = normalize_vector(ortho).flatten()
        return R.from_rotvec(ortho * np.pi).as_matrix().astype(np.float32)

    cross = np.cross(v_from, v_to)
    w = 1.0 + dot
    q = np.array([cross[0], cross[1], cross[2], w], dtype=np.float32)
    q = q / np.linalg.norm(q)
    return R.from_quat(q).as_matrix().astype(np.float32)


def matrix_to_axis_angle(rot_mat: np.ndarray) -> np.ndarray:
    """Convert a 3x3 rotation matrix to a 3D axis-angle (Rodrigues) vector."""
    return R.from_matrix(rot_mat).as_rotvec().astype(np.float32)


def axis_angle_to_matrix(rot_vec: np.ndarray) -> np.ndarray:
    """Convert a 3D axis-angle vector to a 3x3 rotation matrix."""
    return R.from_rotvec(rot_vec).as_matrix().astype(np.float32)


def smooth_landmarks(landmarks: np.ndarray, alpha: float = 0.65) -> np.ndarray:
    """
    Exponential moving average smoothing over sequence of landmarks (F, N, 3).
    Removes high-frequency jitter while preserving sharp sign articulations.
    """
    if len(landmarks) <= 1 or alpha >= 1.0:
        return landmarks

    smoothed = np.empty_like(landmarks)
    smoothed[0] = landmarks[0]
    for t in range(1, len(landmarks)):
        if np.linalg.norm(landmarks[t]) < 1e-5:
            smoothed[t] = smoothed[t - 1]
        else:
            smoothed[t] = alpha * landmarks[t] + (1.0 - alpha) * smoothed[t - 1]
    return smoothed


# ==============================================================================
# 2. BRIDGECONN LANDMARK PREPROCESSING & ISOTROPIC COORDINATE CONVERSION
# ==============================================================================

def clean_and_preprocess_sample(
    npz_path: str,
    smoothing_enabled: bool = True,
    smoothing_alpha: float = 0.70
) -> Dict[str, Any]:
    """
    Loads BridgeConn sample .npz file, cleans missing/zero frames via temporal interpolation,
    converts MediaPipe camera image space to SMPL-X 3D world space isotropically,
    and applies temporal smoothing.

    Coordinate Transformation:
      MediaPipe image space:
        +X: image right (signer's anatomical Left)
        +Y: image down
        +Z: away from camera (depth into scene, normalized)
      SMPL-X world space:
        +X: character's Left
        +Y: character's Up
        +Z: character's Forward (towards camera / viewer)

    Conversion:
      X_smplx =  X_mp
      Y_smplx = -Y_mp
      Z_smplx = -Z_mp * 1920.0  (scale normalized depth isotropically with image pixel width)
    """
    if not os.path.exists(npz_path):
        raise FileNotFoundError(f"BridgeConn sample file not found at: {npz_path}")

    data = np.load(npz_path, allow_pickle=True)
    body_raw = data["body"]            # (F, 33, 3)
    lh_raw = data["left_hand"]         # (F, 21, 3)
    rh_raw = data["right_hand"]        # (F, 21, 3)
    conf = data["confidence"] if "confidence" in data else None
    fps = float(data["fps"]) if "fps" in data and data["fps"].shape == () else 50.0
    gloss = str(data["gloss"]) if "gloss" in data and data["gloss"].shape == () else "sample"

    frames = len(body_raw)
    if frames == 0:
        raise ValueError("Empty animation sequence (0 frames).")

    # Clean zero / missing frames via linear or forward/backward interpolation
    def interpolate_zeros(seq: np.ndarray) -> np.ndarray:
        seq_clean = seq.copy()
        n = len(seq_clean)
        is_zero = np.all(np.abs(seq_clean) < 1e-4, axis=(1, 2))
        if not np.any(is_zero):
            return seq_clean

        # If all frames are zero, return zeros
        if np.all(is_zero):
            return seq_clean

        # Handle leading zeros
        first_valid = int(np.where(~is_zero)[0][0])
        for i in range(first_valid):
            seq_clean[i] = seq_clean[first_valid]

        # Handle trailing zeros
        last_valid = int(np.where(~is_zero)[0][-1])
        for i in range(last_valid + 1, n):
            seq_clean[i] = seq_clean[last_valid]

        # Handle internal zeros with linear interpolation
        i = first_valid
        while i <= last_valid:
            if is_zero[i]:
                # find end of zero segment
                j = i
                while j <= last_valid and is_zero[j]:
                    j += 1
                # interpolate between i-1 and j
                prev_val = seq_clean[i - 1]
                next_val = seq_clean[j]
                for k in range(i, j):
                    t = (k - (i - 1)) / float(j - (i - 1))
                    seq_clean[k] = (1.0 - t) * prev_val + t * next_val
                i = j
            else:
                i += 1
        return seq_clean

    body_clean = interpolate_zeros(body_raw)
    lh_clean = interpolate_zeros(lh_raw)
    rh_clean = interpolate_zeros(rh_raw)

    if smoothing_enabled:
        body_clean = smooth_landmarks(body_clean, alpha=smoothing_alpha)
        lh_clean = smooth_landmarks(lh_clean, alpha=smoothing_alpha)
        rh_clean = smooth_landmarks(rh_clean, alpha=smoothing_alpha)

    # Isotropic depth scaling factor:
    # MediaPipe normalizes depth Z relative to image width. X is in pixels [0, 1920].
    # Multiplying Z by 1920.0 restores metric aspect ratio across X, Y, and Z.
    DEPTH_SCALE = 1920.0

    body_smplx = np.empty_like(body_clean)
    body_smplx[:, :, 0] = body_clean[:, :, 0]
    body_smplx[:, :, 1] = -body_clean[:, :, 1]
    body_smplx[:, :, 2] = -body_clean[:, :, 2] * DEPTH_SCALE

    lh_smplx = np.empty_like(lh_clean)
    lh_smplx[:, :, 0] = lh_clean[:, :, 0]
    lh_smplx[:, :, 1] = -lh_clean[:, :, 1]
    lh_smplx[:, :, 2] = -lh_clean[:, :, 2] * DEPTH_SCALE

    rh_smplx = np.empty_like(rh_clean)
    rh_smplx[:, :, 0] = rh_clean[:, :, 0]
    rh_smplx[:, :, 1] = -rh_clean[:, :, 1]
    rh_smplx[:, :, 2] = -rh_clean[:, :, 2] * DEPTH_SCALE

    return {
        "frames": frames,
        "fps": fps,
        "gloss": gloss,
        "body": body_smplx,
        "left_hand": lh_smplx,
        "right_hand": rh_smplx,
        "confidence": conf,
    }


# ==============================================================================
# 3. MATHEMATICAL SMPL-X SKELETON RETARGETER
# ==============================================================================

class SMPLXRetargeter:
    """
    Retargets cleaned MediaPipe 33-point body and 21-point left/right hands to SMPL-X.
    Computes rigorous hierarchical local rotations for:
      - Stable upright lower body base
      - Natural spine posture tracking
      - Realistic head/neck orientation
      - Kinematically aligned shoulder, elbow, and wrist orientations
      - 30 independent finger joints (15 joints per hand) with correct anatomical flexion
    """

    def __init__(self, device: Optional[torch.device] = None):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Initializing SMPL-X model on device: {self.device}")

        layer_arg = {
            "create_global_orient": False,
            "create_body_pose": False,
            "create_left_hand_pose": False,
            "create_right_hand_pose": False,
            "create_jaw_pose": False,
            "create_leye_pose": False,
            "create_reye_pose": False,
            "create_betas": False,
            "create_expression": False,
            "create_transl": False
        }
        self.model = smplx.create(
            HUMAN_MODEL_PATH,
            "smplx",
            gender="NEUTRAL",
            use_pca=False,
            use_face_contour=False,
            flat_hand_mean=True,
            **layer_arg
        ).to(self.device)
        self.parents = self.model.parents.cpu().numpy()
        self.num_joints = len(self.parents)

        # Precompute rest pose joint locations from neutral template
        v_template = self.model.v_template.unsqueeze(0)  # [1, 10475, 3]
        J_regressor = self.model.J_regressor.unsqueeze(0)  # [1, 55, 10475]
        self.J_rest = torch.matmul(J_regressor, v_template)[0].cpu().numpy()  # [55, 3]

        self._build_rest_frames()

    def _build_rest_frames(self):
        """Precompute rest bone directions and 3D coordinate frames."""
        self.rest_bones: Dict[str, np.ndarray] = {}
        J = self.J_rest

        # Spine rest vectors
        self.rest_bones["pelvis_up"] = normalize_vector(J[9] - J[0])            # spine3 - pelvis (+Y)
        self.rest_bones["pelvis_across"] = normalize_vector(J[1] - J[2])        # L_hip - R_hip (+X)
        self.rest_bones["spine1"] = normalize_vector(J[6] - J[3])               # spine2 - spine1 (+Y)
        self.rest_bones["spine2"] = normalize_vector(J[9] - J[6])               # spine3 - spine2 (+Y)
        self.rest_bones["spine3"] = normalize_vector(J[12] - J[9])              # neck - spine3 (+Y)
        self.rest_bones["neck"] = normalize_vector(J[15] - J[12])               # head - neck (+Y)

        # Arms rest vectors
        self.rest_bones["l_collar"] = normalize_vector(J[16] - J[13])           # L_sh - L_collar (+X)
        self.rest_bones["l_shoulder"] = normalize_vector(J[18] - J[16])         # L_el - L_sh (+X)
        self.rest_bones["l_elbow"] = normalize_vector(J[20] - J[18])            # L_wr - L_el (+X)

        self.rest_bones["r_collar"] = normalize_vector(J[17] - J[14])           # R_sh - R_collar (-X)
        self.rest_bones["r_shoulder"] = normalize_vector(J[19] - J[17])         # R_el - R_sh (-X)
        self.rest_bones["r_elbow"] = normalize_vector(J[21] - J[19])            # R_wr - R_el (-X)

        # ----------------------------------------------------------------------
        # Full 3D Hand Rest Coordinate Frames (Right-Handed, det = +1):
        # ----------------------------------------------------------------------
        # RIGHT HAND:
        #   Along: Middle1 (43) - Wrist (21) -> along -X
        #   Pi: Pinky1 (46) to Index1 (40) -> along +Z
        #   Normal: cross(along, pi) -> along +Y (dorsal / back of hand)
        #   Across: cross(normal, along) -> along +Z
        #   Normal: cross(along, across) -> along +Y
        u_rh_along = normalize_vector(J[43] - J[21])
        u_rh_pi = normalize_vector(J[40] - J[46])
        u_rh_norm = normalize_vector(np.cross(u_rh_along, u_rh_pi))
        u_rh_across = normalize_vector(np.cross(u_rh_norm, u_rh_along))
        u_rh_norm = normalize_vector(np.cross(u_rh_along, u_rh_across))
        self.F_rest_rh = np.column_stack([u_rh_along, u_rh_across, u_rh_norm]).astype(np.float32)

        # LEFT HAND:
        #   Along: Middle1 (28) - Wrist (20) -> along +X
        #   Pi: Pinky1 (31) to Index1 (25) -> along +Z
        #   Normal: cross(pi, along) -> along +Y (dorsal / back of hand)
        #   Across: cross(along, normal) -> along +Z
        #   Normal: cross(across, along) -> along +Y
        u_lh_along = normalize_vector(J[28] - J[20])
        u_lh_pi = normalize_vector(J[25] - J[31])
        u_lh_norm = normalize_vector(np.cross(u_lh_pi, u_lh_along))
        u_lh_across = normalize_vector(np.cross(u_lh_along, u_lh_norm))
        u_lh_norm = normalize_vector(np.cross(u_lh_across, u_lh_along))
        self.F_rest_lh = np.column_stack([u_lh_along, u_lh_across, u_lh_norm]).astype(np.float32)

        # ----------------------------------------------------------------------
        # Rest Finger Bone Directions in Rest Model Space:
        # ----------------------------------------------------------------------
        # Right hand fingers:
        # Index: 40 -> 41 -> 42 -> tip
        self.rest_bones["rh_idx0"] = normalize_vector(J[41] - J[40])
        self.rest_bones["rh_idx1"] = normalize_vector(J[42] - J[41])
        self.rest_bones["rh_idx2"] = normalize_vector(J[42] - J[41])
        # Middle: 43 -> 44 -> 45
        self.rest_bones["rh_mid0"] = normalize_vector(J[44] - J[43])
        self.rest_bones["rh_mid1"] = normalize_vector(J[45] - J[44])
        self.rest_bones["rh_mid2"] = normalize_vector(J[45] - J[44])
        # Pinky: 46 -> 47 -> 48
        self.rest_bones["rh_pnk0"] = normalize_vector(J[47] - J[46])
        self.rest_bones["rh_pnk1"] = normalize_vector(J[48] - J[47])
        self.rest_bones["rh_pnk2"] = normalize_vector(J[48] - J[47])
        # Ring: 49 -> 50 -> 51
        self.rest_bones["rh_rng0"] = normalize_vector(J[50] - J[49])
        self.rest_bones["rh_rng1"] = normalize_vector(J[51] - J[50])
        self.rest_bones["rh_rng2"] = normalize_vector(J[51] - J[50])
        # Thumb: 52 -> 53 -> 54
        self.rest_bones["rh_th0"] = normalize_vector(J[53] - J[52])
        self.rest_bones["rh_th1"] = normalize_vector(J[54] - J[53])
        self.rest_bones["rh_th2"] = normalize_vector(J[54] - J[53])

        # Left hand fingers:
        # Index: 25 -> 26 -> 27
        self.rest_bones["lh_idx0"] = normalize_vector(J[26] - J[25])
        self.rest_bones["lh_idx1"] = normalize_vector(J[27] - J[26])
        self.rest_bones["lh_idx2"] = normalize_vector(J[27] - J[26])
        # Middle: 28 -> 29 -> 30
        self.rest_bones["lh_mid0"] = normalize_vector(J[29] - J[28])
        self.rest_bones["lh_mid1"] = normalize_vector(J[30] - J[29])
        self.rest_bones["lh_mid2"] = normalize_vector(J[30] - J[29])
        # Pinky: 31 -> 32 -> 33
        self.rest_bones["lh_pnk0"] = normalize_vector(J[32] - J[31])
        self.rest_bones["lh_pnk1"] = normalize_vector(J[33] - J[32])
        self.rest_bones["lh_pnk2"] = normalize_vector(J[33] - J[32])
        # Ring: 34 -> 35 -> 36
        self.rest_bones["lh_rng0"] = normalize_vector(J[35] - J[34])
        self.rest_bones["lh_rng1"] = normalize_vector(J[36] - J[35])
        self.rest_bones["lh_rng2"] = normalize_vector(J[36] - J[35])
        # Thumb: 37 -> 38 -> 39
        self.rest_bones["lh_th0"] = normalize_vector(J[38] - J[37])
        self.rest_bones["lh_th1"] = normalize_vector(J[39] - J[38])
        self.rest_bones["lh_th2"] = normalize_vector(J[39] - J[38])

    def retarget_frame(
        self,
        body: np.ndarray,      # (33, 3) in SMPL-X coordinate space
        lh: np.ndarray,        # (21, 3) in SMPL-X coordinate space
        rh: np.ndarray,        # (21, 3) in SMPL-X coordinate space
        prev_wrist_rh: Optional[np.ndarray] = None,
        prev_wrist_lh: Optional[np.ndarray] = None,
        return_state: bool = False
    ) -> Any:
        """
        Retargets a single frame into SMPL-X pose parameters:
            global_orient: (3,)
            body_pose: (63,)  [21 body joints * 3]
            left_hand_pose: (45,) [15 finger joints * 3]
            right_hand_pose: (45,) [15 finger joints * 3]
            transl: (3,)
        """
        # ======================================================================
        # 1. ROOT ORIENTATION & TORSO POSTURE
        # ======================================================================
        G_pelvis = np.eye(3, dtype=np.float32)
        global_orient = np.zeros(3, dtype=np.float32)

        mid_hip = (body[23] + body[24]) / 2.0
        mid_shoulder = (body[11] + body[12]) / 2.0

        # Torso upright & across from shoulders
        torso_up_raw = mid_shoulder - mid_hip
        torso_up = normalize_vector(np.array([
            torso_up_raw[0] * 0.35,
            max(float(torso_up_raw[1]), 1e-3),
            torso_up_raw[2] * 0.15
        ], dtype=np.float32))

        sh_across_raw = body[11] - body[12]  # R_sh -> L_sh (+X)
        sh_across = normalize_vector(np.array([
            sh_across_raw[0],
            sh_across_raw[1] * 0.25,
            sh_across_raw[2] * 0.25
        ], dtype=np.float32))
        sh_fwd = normalize_vector(np.cross(sh_across, torso_up))
        if sh_fwd[2] < 0:
            sh_fwd = -sh_fwd
        sh_across = normalize_vector(np.cross(torso_up, sh_fwd))

        G_torso = np.column_stack([sh_across, torso_up, sh_fwd]).astype(np.float32)

        rotvec_spine = matrix_to_axis_angle(G_torso) * 0.20
        R_spine_step = R.from_rotvec(rotvec_spine).as_matrix().astype(np.float32)

        G_spine1 = R_spine_step @ G_pelvis
        G_spine2 = R_spine_step @ G_spine1
        G_spine3 = R_spine_step @ G_spine2

        # ======================================================================
        # 2. HEAD & NECK ORIENTATION
        # ======================================================================
        ear_vec = body[7] - body[8]
        if np.linalg.norm(ear_vec) < 1e-3:
            ear_vec = body[2] - body[5]
        if np.linalg.norm(ear_vec) < 1e-3:
            ear_vec = np.array([1.0, 0.0, 0.0], dtype=np.float32)

        head_across = normalize_vector(np.array([
            ear_vec[0],
            ear_vec[1] * 0.35,
            ear_vec[2] * 0.35
        ], dtype=np.float32))

        head_up = normalize_vector(np.array([-head_across[1], head_across[0], 0.0], dtype=np.float32))
        if head_up[1] < 0:
            head_up = -head_up
        if np.linalg.norm(head_up) < 1e-3:
            head_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        head_fwd = normalize_vector(np.cross(head_across, head_up))
        if head_fwd[2] < 0:
            head_fwd = -head_fwd
        head_across = normalize_vector(np.cross(head_up, head_fwd))

        G_head = np.column_stack([head_across, head_up, head_fwd]).astype(np.float32)
        G_neck = G_spine3.copy()

        # ======================================================================
        # 3. COLLARS & SHOULDERS
        # ======================================================================
        # Two-hand interaction proximity factor:
        has_lh_contact = np.linalg.norm(lh[0]) > 1e-4 and np.linalg.norm(lh[9] - lh[0]) > 1e-4
        has_rh_contact = np.linalg.norm(rh[0]) > 1e-4 and np.linalg.norm(rh[9] - rh[0]) > 1e-4

        if has_lh_contact and has_rh_contact:
            lh_center = (lh[0] + lh[9]) / 2.0
            rh_center = (rh[0] + rh[9]) / 2.0
            d_hands = float(np.linalg.norm(rh_center - lh_center))
            # Smooth contact factor: 0.0 when d >= 220 units (~0.22m), smoothly increases to 1.0 when d <= 80 units
            w_contact = float(np.clip((220.0 - d_hands) / 140.0, 0.0, 1.0))
        else:
            d_hands = 1000.0
            w_contact = 0.0

        # When hands approach midline contact, relax clavicle clamp from 0.72 towards 0.40
        # and allow slight forward protraction (+Z) so the avatar's hands meet naturally without shoulder collapse
        clamp_x = float(0.72 - 0.32 * w_contact)
        protract_z = float(0.20 + 0.25 * w_contact)

        u_l_collar = normalize_vector(body[11] - mid_shoulder)
        u_r_collar = normalize_vector(body[12] - mid_shoulder)

        u_l_collar_stab = normalize_vector(np.array([
            max(float(u_l_collar[0]), clamp_x),
            u_l_collar[1] * 0.25,
            u_l_collar[2] * protract_z
        ], dtype=np.float32))
        u_r_collar_stab = normalize_vector(np.array([
            min(float(u_r_collar[0]), -clamp_x),
            u_r_collar[1] * 0.25,
            u_r_collar[2] * protract_z
        ], dtype=np.float32))

        G_l_collar = rotation_between_vectors(self.rest_bones["l_collar"], u_l_collar_stab)
        G_r_collar = rotation_between_vectors(self.rest_bones["r_collar"], u_r_collar_stab)

        # ======================================================================
        # 4. KINEMATIC ARMS, WRISTS & 3D HAND BASES
        # ======================================================================
        # --- RIGHT ARM & WRIST ---
        u_r_upper = normalize_vector(body[14] - body[12])   # R_sh -> R_el
        u_r_forearm = normalize_vector(body[16] - body[14]) # R_el -> R_wr

        # Elbow flexion plane normal
        r_bend_cross = np.cross(u_r_upper, u_r_forearm)
        r_bend_norm = np.linalg.norm(r_bend_cross)
        if r_bend_norm > 0.05:
            n_r_arm = r_bend_cross / r_bend_norm
        else:
            n_r_arm = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        # Rigid 3D basis for upper arm
        u_r_up_perp = normalize_vector(np.cross(u_r_upper, n_r_arm))
        F_target_r_sh = np.column_stack([u_r_upper, n_r_arm, u_r_up_perp])
        b_r_sh_rest = self.rest_bones["r_shoulder"]
        n_sh_rest = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        u_r_up_perp_rest = normalize_vector(np.cross(b_r_sh_rest, n_sh_rest))
        F_rest_r_sh = np.column_stack([b_r_sh_rest, n_sh_rest, u_r_up_perp_rest])
        G_r_shoulder = F_target_r_sh @ F_rest_r_sh.T

        # Right Hand 3D Orientation Frame
        rh_w = rh[0]
        rh_idx = rh[5]
        rh_mid = rh[9]
        rh_pnk = rh[17]

        rh_along = rh_mid - rh_w
        has_rh_orient = np.linalg.norm(rh_along) > 1e-4
        if has_rh_orient:
            u_rh_along = normalize_vector(rh_along)
            u_rh_pi = normalize_vector(rh_idx - rh_pnk)     # pinky to index (+Z)
            u_rh_norm = normalize_vector(np.cross(u_rh_along, u_rh_pi)) # dorsal (+Y in rest)
            u_rh_across = normalize_vector(np.cross(u_rh_norm, u_rh_along))
            u_rh_norm = normalize_vector(np.cross(u_rh_along, u_rh_across))

            F_target_rh = np.column_stack([u_rh_along, u_rh_across, u_rh_norm])
            G_r_wrist = F_target_rh @ self.F_rest_rh.T

            # Face proximity semantic invariant check (resolves monocular depth reflection e.g. DRINK):
            # When hand is near head/mouth and palm faces directly away into empty space, resolve the 180° flip
            mid_head = (body[0] + (body[7] + body[8]) / 2.0) / 2.0
            to_face = normalize_vector(mid_head - rh_w)
            palm_norm = -G_r_wrist[:, 2] # in F_rest_rh column 2 is dorsal (+Y), palm is -column 2
            dot_face = float(np.dot(palm_norm, to_face))
            d_face = float(np.linalg.norm(rh_w - mid_head))

            if d_face < 280.0 and dot_face < -0.15:
                R_flip = R.from_rotvec(u_rh_along * np.pi).as_matrix().astype(np.float32)
                G_r_wrist = R_flip @ G_r_wrist

            # Temporal continuity check against previous frame wrist orientation
            if prev_wrist_rh is not None:
                R_rel = G_r_wrist @ prev_wrist_rh.T
                tr = float(np.clip(np.trace(R_rel), -1.0, 3.0))
                angle = float(np.arccos(np.clip((tr - 1.0) / 2.0, -1.0, 1.0)))

                if angle > np.pi / 2.0:  # > 90 degrees jump
                    R_flip = R.from_rotvec(u_rh_along * np.pi).as_matrix().astype(np.float32)
                    G_r_wrist_flipped = R_flip @ G_r_wrist

                    R_rel_flipped = G_r_wrist_flipped @ prev_wrist_rh.T
                    tr_flipped = float(np.clip(np.trace(R_rel_flipped), -1.0, 3.0))
                    angle_flipped = float(np.arccos(np.clip((tr_flipped - 1.0) / 2.0, -1.0, 1.0)))

                    if angle_flipped < angle:
                        G_r_wrist = G_r_wrist_flipped
                        angle = angle_flipped

                # If still > 60 deg (ambiguous/occluded landmark noise), coast from prev_wrist_rh:
                if angle > np.deg2rad(60.0):
                    slerp_t = float(np.deg2rad(45.0) / angle)
                    r_rel_rotvec = R.from_matrix(G_r_wrist @ prev_wrist_rh.T).as_rotvec()
                    G_r_wrist = R.from_rotvec(r_rel_rotvec * slerp_t).as_matrix().astype(np.float32) @ prev_wrist_rh

            # Forearm pronation/supination coupling:
            # Derive dorsal normal directly from continuous G_r_wrist (rest dorsal is +Y)
            v_r_dorsal_cont = G_r_wrist @ np.array([0.0, 1.0, 0.0], dtype=np.float32)
            v_r_dorsal = v_r_dorsal_cont - np.dot(v_r_dorsal_cont, u_r_forearm) * u_r_forearm
            if np.linalg.norm(v_r_dorsal) > 0.1:
                v_r_dorsal = normalize_vector(v_r_dorsal)
                n_r_arm_rolled = normalize_vector(0.45 * n_r_arm + 0.55 * v_r_dorsal)
            else:
                n_r_arm_rolled = n_r_arm
        else:
            n_r_arm_rolled = n_r_arm

        # Rigid 3D basis for forearm
        u_r_fore_perp = normalize_vector(np.cross(u_r_forearm, n_r_arm_rolled))
        F_target_r_el = np.column_stack([u_r_forearm, n_r_arm_rolled, u_r_fore_perp])
        b_r_el_rest = self.rest_bones["r_elbow"]
        u_r_fore_perp_rest = normalize_vector(np.cross(b_r_el_rest, n_sh_rest))
        F_rest_r_el = np.column_stack([b_r_el_rest, n_sh_rest, u_r_fore_perp_rest])
        G_r_elbow = F_target_r_el @ F_rest_r_el.T

        if not has_rh_orient:
            G_r_wrist = G_r_elbow.copy()

        # --- LEFT ARM & WRIST ---
        u_l_upper = normalize_vector(body[13] - body[11])   # L_sh -> L_el
        u_l_forearm = normalize_vector(body[15] - body[13]) # L_el -> L_wr

        l_bend_cross = np.cross(u_l_forearm, u_l_upper)
        l_bend_norm = np.linalg.norm(l_bend_cross)
        if l_bend_norm > 0.05:
            n_l_arm = l_bend_cross / l_bend_norm
        else:
            n_l_arm = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        # Rigid 3D basis for upper arm
        u_l_up_perp = normalize_vector(np.cross(n_l_arm, u_l_upper))
        F_target_l_sh = np.column_stack([u_l_upper, n_l_arm, u_l_up_perp])
        b_l_sh_rest = self.rest_bones["l_shoulder"]
        u_l_up_perp_rest = normalize_vector(np.cross(n_sh_rest, b_l_sh_rest))
        F_rest_l_sh = np.column_stack([b_l_sh_rest, n_sh_rest, u_l_up_perp_rest])
        G_l_shoulder = F_target_l_sh @ F_rest_l_sh.T

        # Left Hand 3D Orientation Frame
        lh_w = lh[0]
        lh_idx = lh[5]
        lh_mid = lh[9]
        lh_pnk = lh[17]

        lh_along = lh_mid - lh_w
        has_lh_orient = np.linalg.norm(lh_along) > 1e-4
        if has_lh_orient:
            u_lh_along = normalize_vector(lh_along)
            u_lh_pi = normalize_vector(lh_idx - lh_pnk)     # pinky to index (+Z)
            u_lh_norm = normalize_vector(np.cross(u_lh_pi, u_lh_along)) # dorsal (+Y)
            u_lh_across = normalize_vector(np.cross(u_lh_along, u_lh_norm))
            u_lh_norm = normalize_vector(np.cross(u_lh_across, u_lh_along))

            F_target_lh = np.column_stack([u_lh_along, u_lh_across, u_lh_norm])
            G_l_wrist = F_target_lh @ self.F_rest_lh.T

            # Temporal continuity check against previous frame wrist orientation
            if prev_wrist_lh is not None:
                R_rel = G_l_wrist @ prev_wrist_lh.T
                tr = float(np.clip(np.trace(R_rel), -1.0, 3.0))
                angle = float(np.arccos(np.clip((tr - 1.0) / 2.0, -1.0, 1.0)))

                if angle > np.pi / 2.0:
                    R_flip = R.from_rotvec(u_lh_along * np.pi).as_matrix().astype(np.float32)
                    G_l_wrist_flipped = R_flip @ G_l_wrist

                    R_rel_flipped = G_l_wrist_flipped @ prev_wrist_lh.T
                    tr_flipped = float(np.clip(np.trace(R_rel_flipped), -1.0, 3.0))
                    angle_flipped = float(np.arccos(np.clip((tr_flipped - 1.0) / 2.0, -1.0, 1.0)))

                    if angle_flipped < angle:
                        G_l_wrist = G_l_wrist_flipped
                        angle = angle_flipped

                # If still > 60 deg (ambiguous/occluded landmark noise), coast from prev_wrist_lh:
                if angle > np.deg2rad(60.0):
                    slerp_t = float(np.deg2rad(45.0) / angle)
                    r_rel_rotvec = R.from_matrix(G_l_wrist @ prev_wrist_lh.T).as_rotvec()
                    G_l_wrist = R.from_rotvec(r_rel_rotvec * slerp_t).as_matrix().astype(np.float32) @ prev_wrist_lh

            # Forearm pronation/supination coupling:
            # Derive dorsal normal directly from continuous G_l_wrist
            v_l_dorsal_cont = G_l_wrist @ np.array([0.0, 1.0, 0.0], dtype=np.float32)
            v_l_dorsal = v_l_dorsal_cont - np.dot(v_l_dorsal_cont, u_l_forearm) * u_l_forearm
            if np.linalg.norm(v_l_dorsal) > 0.1:
                v_l_dorsal = normalize_vector(v_l_dorsal)
                n_l_arm_rolled = normalize_vector(0.45 * n_l_arm + 0.55 * v_l_dorsal)
            else:
                n_l_arm_rolled = n_l_arm
        else:
            n_l_arm_rolled = n_l_arm

        # Rigid 3D basis for forearm
        u_l_fore_perp = normalize_vector(np.cross(n_l_arm_rolled, u_l_forearm))
        F_target_l_el = np.column_stack([u_l_forearm, n_l_arm_rolled, u_l_fore_perp])
        b_l_el_rest = self.rest_bones["l_elbow"]
        u_l_fore_perp_rest = normalize_vector(np.cross(n_sh_rest, b_l_el_rest))
        F_rest_l_el = np.column_stack([b_l_el_rest, n_sh_rest, u_l_fore_perp_rest])
        G_l_elbow = F_target_l_el @ F_rest_l_el.T

        if not has_lh_orient:
            G_l_wrist = G_l_elbow.copy()

        # ======================================================================
        # 5. LOCAL BODY ROTATIONS (21 joints in SMPL-X body_pose)
        # ======================================================================
        # 1: L_Hip, 2: R_Hip, 3: Spine_1, 4: L_Knee, 5: R_Knee, 6: Spine_2, 7: L_Ankle, 8: R_Ankle,
        # 9: Spine_3, 10: L_Foot, 11: R_Foot, 12: Neck, 13: L_Collar, 14: R_Collar, 15: Head,
        # 16: L_Shoulder, 17: R_Shoulder, 18: L_Elbow, 19: R_Elbow, 20: L_Wrist, 21: R_Wrist
        body_rots = np.zeros((21, 3), dtype=np.float32)

        # Stable neutral standing base for legs
        body_rots[0] = np.zeros(3, dtype=np.float32)                     # 1: L_Hip
        body_rots[1] = np.zeros(3, dtype=np.float32)                     # 2: R_Hip
        body_rots[2] = matrix_to_axis_angle(G_pelvis.T @ G_spine1)       # 3: Spine_1

        body_rots[3] = np.array([0.02, 0.0, 0.0], dtype=np.float32)     # 4: L_Knee
        body_rots[4] = np.array([0.02, 0.0, 0.0], dtype=np.float32)     # 5: R_Knee
        body_rots[5] = matrix_to_axis_angle(G_spine1.T @ G_spine2)       # 6: Spine_2

        body_rots[6] = np.zeros(3, dtype=np.float32)                     # 7: L_Ankle
        body_rots[7] = np.zeros(3, dtype=np.float32)                     # 8: R_Ankle
        body_rots[8] = matrix_to_axis_angle(G_spine2.T @ G_spine3)       # 9: Spine_3

        body_rots[9] = np.zeros(3, dtype=np.float32)                     # 10: L_Foot
        body_rots[10] = np.zeros(3, dtype=np.float32)                    # 11: R_Foot

        # Neck & Head
        body_rots[11] = matrix_to_axis_angle(G_spine3.T @ G_neck)        # 12: Neck
        body_rots[12] = matrix_to_axis_angle(G_spine3.T @ G_l_collar)    # 13: L_Collar
        body_rots[13] = matrix_to_axis_angle(G_spine3.T @ G_r_collar)    # 14: R_Collar
        body_rots[14] = matrix_to_axis_angle(G_neck.T @ G_head)          # 15: Head

        # Shoulders (parent: Collar)
        body_rots[15] = matrix_to_axis_angle(G_l_collar.T @ G_l_shoulder) # 16: L_Shoulder
        body_rots[16] = matrix_to_axis_angle(G_r_collar.T @ G_r_shoulder) # 17: R_Shoulder

        # Elbows (parent: Shoulder)
        body_rots[17] = matrix_to_axis_angle(G_l_shoulder.T @ G_l_elbow)  # 18: L_Elbow
        body_rots[18] = matrix_to_axis_angle(G_r_shoulder.T @ G_r_elbow)  # 19: R_Elbow

        # Wrists (parent: Elbow)
        body_rots[19] = matrix_to_axis_angle(G_l_elbow.T @ G_l_wrist)     # 20: L_Wrist
        body_rots[20] = matrix_to_axis_angle(G_r_elbow.T @ G_r_wrist)     # 21: R_Wrist

        body_pose = body_rots.flatten()

        # ======================================================================
        # 6. HIERARCHICAL FINGER ARTICULATION (15 joints per hand)
        # ======================================================================
        def retarget_hand_finger_chain(
            landmarks: np.ndarray,
            indices: Tuple[int, int, int, int],
            rest_keys: Tuple[str, str, str],
            G_wrist: np.ndarray
        ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
            """
            Computes hierarchical joint rotations for 3 phalanges of a finger.
            Transforms world-space bone vectors into hand's rest coordinate system,
            then calculates sequential local rotations R0, R1, R2.
            """
            p0, p1, p2, p3 = indices
            u0 = normalize_vector(landmarks[p1] - landmarks[p0])
            u1 = normalize_vector(landmarks[p2] - landmarks[p1])
            u2 = normalize_vector(landmarks[p3] - landmarks[p2])

            # Express observed bone directions in the hand's local rest frame
            v0 = G_wrist.T @ u0
            v1 = G_wrist.T @ u1
            v2 = G_wrist.T @ u2

            b0_rest = self.rest_bones[rest_keys[0]]
            b1_rest = self.rest_bones[rest_keys[1]]
            b2_rest = self.rest_bones[rest_keys[2]]

            R0 = rotation_between_vectors(b0_rest, v0)
            R1 = rotation_between_vectors(b1_rest, R0.T @ v1)
            R2 = rotation_between_vectors(b2_rest, (R0 @ R1).T @ v2)

            r0 = matrix_to_axis_angle(R0)
            r1 = matrix_to_axis_angle(R1)
            r2 = matrix_to_axis_angle(R2)
            return r0, r1, r2

        # --- RIGHT HAND FINGERS ---
        rh_rots = np.zeros((15, 3), dtype=np.float32)
        if np.linalg.norm(rh[9] - rh[0]) > 1e-4:
            # Index (joints 40, 41, 42 -> slots 0, 1, 2)
            rh_rots[0], rh_rots[1], rh_rots[2] = retarget_hand_finger_chain(
                rh, (5, 6, 7, 8), ("rh_idx0", "rh_idx1", "rh_idx2"), G_r_wrist
            )
            # Middle (joints 43, 44, 45 -> slots 3, 4, 5)
            rh_rots[3], rh_rots[4], rh_rots[5] = retarget_hand_finger_chain(
                rh, (9, 10, 11, 12), ("rh_mid0", "rh_mid1", "rh_mid2"), G_r_wrist
            )
            # Pinky (joints 46, 47, 48 -> slots 6, 7, 8)
            rh_rots[6], rh_rots[7], rh_rots[8] = retarget_hand_finger_chain(
                rh, (17, 18, 19, 20), ("rh_pnk0", "rh_pnk1", "rh_pnk2"), G_r_wrist
            )
            # Ring (joints 49, 50, 51 -> slots 9, 10, 11)
            rh_rots[9], rh_rots[10], rh_rots[11] = retarget_hand_finger_chain(
                rh, (13, 14, 15, 16), ("rh_rng0", "rh_rng1", "rh_rng2"), G_r_wrist
            )
            # Thumb (joints 52, 53, 54 -> slots 12, 13, 14)
            rh_rots[12], rh_rots[13], rh_rots[14] = retarget_hand_finger_chain(
                rh, (1, 2, 3, 4), ("rh_th0", "rh_th1", "rh_th2"), G_r_wrist
            )
        right_hand_pose = rh_rots.flatten()

        # --- LEFT HAND FINGERS ---
        lh_rots = np.zeros((15, 3), dtype=np.float32)
        if np.linalg.norm(lh[9] - lh[0]) > 1e-4:
            # Index (joints 25, 26, 27 -> slots 0, 1, 2)
            lh_rots[0], lh_rots[1], lh_rots[2] = retarget_hand_finger_chain(
                lh, (5, 6, 7, 8), ("lh_idx0", "lh_idx1", "lh_idx2"), G_l_wrist
            )
            # Middle (joints 28, 29, 30 -> slots 3, 4, 5)
            lh_rots[3], lh_rots[4], lh_rots[5] = retarget_hand_finger_chain(
                lh, (9, 10, 11, 12), ("lh_mid0", "lh_mid1", "lh_mid2"), G_l_wrist
            )
            # Pinky (joints 31, 32, 33 -> slots 6, 7, 8)
            lh_rots[6], lh_rots[7], lh_rots[8] = retarget_hand_finger_chain(
                lh, (17, 18, 19, 20), ("lh_pnk0", "lh_pnk1", "lh_pnk2"), G_l_wrist
            )
            # Ring (joints 34, 35, 36 -> slots 9, 10, 11)
            lh_rots[9], lh_rots[10], lh_rots[11] = retarget_hand_finger_chain(
                lh, (13, 14, 15, 16), ("lh_rng0", "lh_rng1", "lh_rng2"), G_l_wrist
            )
            # Thumb (joints 37, 38, 39 -> slots 12, 13, 14)
            lh_rots[12], lh_rots[13], lh_rots[14] = retarget_hand_finger_chain(
                lh, (1, 2, 3, 4), ("lh_th0", "lh_th1", "lh_th2"), G_l_wrist
            )
        left_hand_pose = lh_rots.flatten()

        # Pelvis translation remains centered
        transl = np.zeros(3, dtype=np.float32)

        if return_state:
            frame_state = {
                "G_r_wrist": G_r_wrist,
                "G_l_wrist": G_l_wrist,
                "G_r_elbow": G_r_elbow,
                "G_l_elbow": G_l_elbow,
                "G_r_shoulder": G_r_shoulder,
                "G_l_shoulder": G_l_shoulder,
            }
            return global_orient, body_pose, left_hand_pose, right_hand_pose, transl, frame_state

        return global_orient, body_pose, left_hand_pose, right_hand_pose, transl

    def retarget_sequence(
        self,
        cleaned_data: Dict[str, Any],
        batch_size: int = 32
    ) -> Tuple[np.ndarray, Dict[str, Any], Dict[str, Any]]:
        """
        Retargets all frames of the sequence and runs SMPL-X forward pass
        to generate (frames, 10475, 3) vertex animation.
        """
        frames = cleaned_data["frames"]
        body_seq = cleaned_data["body"]
        lh_seq = cleaned_data["left_hand"]
        rh_seq = cleaned_data["right_hand"]

        logger.info(f"Retargeting {frames} frames with full body and 30-joint finger articulation...")

        global_orients = []
        body_poses = []
        lh_poses = []
        rh_poses = []
        transls = []

        prev_wrist_rh = None
        prev_wrist_lh = None

        for i in range(frames):
            body_frame = body_seq[i].copy()
            lh_frame = lh_seq[i].copy()
            rh_frame = rh_seq[i].copy()

            # Occlusion-aware contact prior (e.g. for TEACHER):
            # If left index finger is upright (shaft points upward Y > 0.60) and right hand approaches
            # within interaction proximity envelope (d < 220 units ~ 0.22m) with tracking uncertainty:
            lh_upright = False
            if np.linalg.norm(lh_frame[9] - lh_frame[0]) > 1e-4:
                idx_vec = lh_frame[8] - lh_frame[5] # index MCP -> index tip
                if np.linalg.norm(idx_vec) > 1e-4:
                    idx_dir = normalize_vector(idx_vec)
                    if idx_dir[1] > 0.60: # upright index finger
                        lh_upright = True

            if lh_upright and np.linalg.norm(rh_frame[9] - rh_frame[0]) > 1e-4:
                rh_center = (rh_frame[0] + rh_frame[9]) / 2.0
                lh_idx_tip = lh_frame[8]
                d_contact = float(np.linalg.norm(rh_center - lh_idx_tip))
                if d_contact < 220.0:
                    # Non-dominant upright index acts as spatial anchor; guide right hand toward contact shaft
                    w_occ = float(np.clip((220.0 - d_contact) / 120.0, 0.0, 0.65))
                    target_contact = (lh_frame[5] + lh_frame[8]) / 2.0 # center of index shaft
                    offset = (target_contact - rh_center) * w_occ
                    rh_frame += offset

            res = self.retarget_frame(
                body_frame, lh_frame, rh_frame,
                prev_wrist_rh=prev_wrist_rh,
                prev_wrist_lh=prev_wrist_lh,
                return_state=True
            )
            go, bp, lhp, rhp, tr, frame_state = res
            prev_wrist_rh = frame_state["G_r_wrist"]
            prev_wrist_lh = frame_state["G_l_wrist"]

            global_orients.append(go)
            body_poses.append(bp)
            lh_poses.append(lhp)
            rh_poses.append(rhp)
            transls.append(tr)

        global_orients = np.array(global_orients, dtype=np.float32)
        body_poses = np.array(body_poses, dtype=np.float32)
        lh_poses = np.array(lh_poses, dtype=np.float32)
        rh_poses = np.array(rh_poses, dtype=np.float32)
        transls = np.array(transls, dtype=np.float32)

        logger.info(f"Running SMPL-X forward pass on {self.device}...")
        all_vertices = []

        with torch.no_grad():
            for start in range(0, frames, batch_size):
                end = min(start + batch_size, frames)
                b_size = end - start

                b_go = torch.tensor(global_orients[start:end], device=self.device)
                b_bp = torch.tensor(body_poses[start:end], device=self.device)
                b_lhp = torch.tensor(lh_poses[start:end], device=self.device)
                b_rhp = torch.tensor(rh_poses[start:end], device=self.device)
                b_tr = torch.tensor(transls[start:end], device=self.device)

                b_betas = torch.zeros((b_size, 10), dtype=torch.float32, device=self.device)
                b_expr = torch.zeros((b_size, 10), dtype=torch.float32, device=self.device)
                b_jaw = torch.zeros((b_size, 3), dtype=torch.float32, device=self.device)
                b_leye = torch.zeros((b_size, 3), dtype=torch.float32, device=self.device)
                b_reye = torch.zeros((b_size, 3), dtype=torch.float32, device=self.device)

                output = self.model(
                    global_orient=b_go,
                    body_pose=b_bp,
                    left_hand_pose=b_lhp,
                    right_hand_pose=b_rhp,
                    transl=b_tr,
                    betas=b_betas,
                    expression=b_expr,
                    jaw_pose=b_jaw,
                    leye_pose=b_leye,
                    reye_pose=b_reye,
                    return_verts=True
                )

                verts_batch = output.vertices.cpu().numpy().astype(np.float32)
                all_vertices.append(verts_batch)

        vertices = np.concatenate(all_vertices, axis=0)  # (frames, 10475, 3)

        pose_params = {
            "global_orient": global_orients,
            "body_pose": body_poses,
            "left_hand_pose": lh_poses,
            "right_hand_pose": rh_poses,
            "transl": transls,
            "fps": cleaned_data["fps"],
            "gloss": cleaned_data["gloss"]
        }

        metadata = {
            "source": "BridgeConn Sign Dictionary ISL",
            "gloss": cleaned_data["gloss"],
            "frames": frames,
            "fps": cleaned_data["fps"],
            "vertices": 10475,
            "vertex_shape": list(vertices.shape),
            "coordinate_system": "SMPL-X",
            "hands_used": True,
            "face_used": False
        }

        return vertices, metadata, pose_params


# ==============================================================================
# 4. CONVERSION PIPELINE ENTRYPOINT
# ==============================================================================

def convert_bridgeconn_sample(
    npz_path: str,
    output_npy_path: Optional[str] = None,
    output_json_path: Optional[str] = None,
    output_params_npz_path: Optional[str] = None
) -> Tuple[str, str, str]:
    """
    Complete end-to-end retargeting pipeline:
    1. Loads sample .npz
    2. Cleans landmarks & normalizes coordinates isotropically
    3. Retargets body and hands to SMPL-X pose parameters
    4. Evaluates SMPL-X forward pass
    5. Saves (frames, 10475, 3) .npy, metadata .json, and pose parameters .npz
    """
    cleaned = clean_and_preprocess_sample(npz_path)
    gloss = cleaned["gloss"]

    out_dir = os.path.join(BASE_DIR, "outputs", "npy")
    os.makedirs(out_dir, exist_ok=True)

    if output_npy_path is None:
        output_npy_path = os.path.join(out_dir, f"{gloss}.npy")
    if output_json_path is None:
        output_json_path = os.path.join(out_dir, f"{gloss}.json")
    if output_params_npz_path is None:
        output_params_npz_path = os.path.join(out_dir, f"{gloss}_smplx_params.npz")

    # Ensure parent directories exist
    os.makedirs(os.path.dirname(os.path.abspath(output_npy_path)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(output_json_path)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(output_params_npz_path)), exist_ok=True)

    retargeter = SMPLXRetargeter()
    vertices, metadata, pose_params = retargeter.retarget_sequence(cleaned)

    # Save NPY
    np.save(output_npy_path, vertices)
    logger.info(f"Saved animation vertices to: {output_npy_path} (Shape: {vertices.shape}, Dtype: {vertices.dtype})")

    # Save JSON metadata
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
    logger.info(f"Saved animation metadata to: {output_json_path}")

    # Save SMPL-X pose parameters NPZ
    np.savez_compressed(
        output_params_npz_path,
        global_orient=pose_params["global_orient"],
        body_pose=pose_params["body_pose"],
        left_hand_pose=pose_params["left_hand_pose"],
        right_hand_pose=pose_params["right_hand_pose"],
        transl=pose_params["transl"],
        fps=pose_params["fps"],
        gloss=pose_params["gloss"]
    )
    logger.info(f"Saved SMPL-X pose parameters to: {output_params_npz_path}")

    return output_npy_path, output_json_path, output_params_npz_path


if __name__ == "__main__":
    test_npz = os.path.join(BASE_DIR, "bridgeconn_samples", "sample_1.npz")
    if not os.path.exists(test_npz):
        test_npz = r"D:\SignAuraData\BridgeConn\extracted\poses\1160_drink.npz"
    convert_bridgeconn_sample(test_npz)
