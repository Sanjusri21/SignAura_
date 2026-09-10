"""
BridgeConn ISL to SMPL-X 3D Animation Retargeting Pipeline.

Retargets MediaPipe body landmarks (33) and hand landmarks (21 left, 21 right)
from the BridgeConn ISL dataset into SMPL-X joint rotations and produces
(frames, 10475, 3) vertex animation compatible with SignAvatars.
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
# 1. VECTOR & ROTATION MATH HELPERS
# ==============================================================================

def normalize_vector(v: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    """Normalize 1D or 2D vectors along the last axis safely."""
    norm = np.linalg.norm(v, axis=-1, keepdims=True)
    norm = np.where(norm < eps, eps, norm)
    return v / norm


def rotation_between_vectors(v_from: np.ndarray, v_to: np.ndarray) -> np.ndarray:
    """
    Computes the shortest arc rotation matrix (3x3) that maps unit vector v_from to v_to.
    Uses robust Rodrigues / quaternion formulation without singularities.
    """
    v_from = normalize_vector(v_from).flatten()
    v_to = normalize_vector(v_to).flatten()

    dot = float(np.dot(v_from, v_to))
    
    # Vectors are nearly identical -> Identity
    if dot > 0.9999999:
        return np.eye(3, dtype=np.float32)
    
    # Vectors are opposite -> 180 deg rotation around orthogonal axis
    if dot < -0.9999999:
        # Find an orthogonal axis
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
    """Convert a 3x3 rotation matrix to a 3D axis-angle vector."""
    return R.from_matrix(rot_mat).as_rotvec().astype(np.float32)


def smooth_landmarks(landmarks: np.ndarray, alpha: float = 0.6) -> np.ndarray:
    """
    Exponential moving average smoothing over sequence of landmarks (F, N, 3).
    Removes jitter while preserving fast articulation.
    """
    if len(landmarks) <= 1 or alpha >= 1.0:
        return landmarks
    
    smoothed = np.empty_like(landmarks)
    smoothed[0] = landmarks[0]
    for t in range(1, len(landmarks)):
        # If current frame is missing/zero, keep previous
        if np.linalg.norm(landmarks[t]) < 1e-5:
            smoothed[t] = smoothed[t - 1]
        else:
            smoothed[t] = alpha * landmarks[t] + (1.0 - alpha) * smoothed[t - 1]
    return smoothed


# ==============================================================================
# 2. BRIDGECONN LANDMARK PREPROCESSING & COORDINATE CONVERSION
# ==============================================================================

def clean_and_preprocess_sample(
    npz_path: str,
    smoothing_enabled: bool = True,
    smoothing_alpha: float = 0.7
) -> Dict[str, Any]:
    """
    Loads BridgeConn sample .npz file, validates arrays, converts coordinates
    to SMPL-X space, cleans invalid/missing landmarks, and applies temporal smoothing.
    """
    if not os.path.exists(npz_path):
        raise FileNotFoundError(f"BridgeConn sample file not found at: {npz_path}")

    data = np.load(npz_path, allow_pickle=True)
    body_raw = data["body"]            # (F, 33, 3)
    lh_raw = data["left_hand"]         # (F, 21, 3)
    rh_raw = data["right_hand"]        # (F, 21, 3)
    conf = data["confidence"] if "confidence" in data else None
    fps = float(data["fps"]) if "fps" in data and data["fps"].shape == () else 50.0
    gloss = str(data["gloss"]) if "gloss" in data and data["gloss"].shape == () else "sample_1"

    frames = len(body_raw)
    if frames == 0:
        raise ValueError("Empty animation sequence (0 frames).")

    # Clean zero/invalid frames using interpolation
    def interpolate_zeros(seq: np.ndarray) -> np.ndarray:
        seq_clean = seq.copy()
        for i in range(len(seq_clean)):
            # If all landmarks in frame are near zero
            if np.all(np.abs(seq_clean[i]) < 1e-4):
                if i > 0:
                    seq_clean[i] = seq_clean[i - 1]
                else:
                    # Find first valid frame
                    for j in range(1, len(seq_clean)):
                        if not np.all(np.abs(seq_clean[j]) < 1e-4):
                            seq_clean[0] = seq_clean[j]
                            break
        return seq_clean

    body_clean = interpolate_zeros(body_raw)
    lh_clean = interpolate_zeros(lh_raw)
    rh_clean = interpolate_zeros(rh_raw)

    if smoothing_enabled:
        body_clean = smooth_landmarks(body_clean, alpha=smoothing_alpha)
        lh_clean = smooth_landmarks(lh_clean, alpha=smoothing_alpha)
        rh_clean = smooth_landmarks(rh_clean, alpha=smoothing_alpha)

    # --------------------------------------------------------------------------
    # COORDINATE SYSTEM CONVERSION:
    # MediaPipe 2D/3D camera image space -> SMPL-X 3D world space
    #
    # MediaPipe:
    #   +X: Person's Left side (right side in image)
    #   +Y: Downwards in image
    #   +Z: Depth (negative = closer to camera / front)
    #
    # SMPL-X:
    #   +X: Character's Left
    #   +Y: Character's Upwards
    #   +Z: Character's Front (forward)
    #
    # Conversion:
    #   X_smplx = +X_mp
    #   Y_smplx = -Y_mp  (flip vertical so up is +Y)
    #   Z_smplx = -Z_mp  (flip depth so front is +Z)
    # --------------------------------------------------------------------------

    # Scale factor for depth if needed (MediaPipe depth is normalized relative to width)
    # For body: calculate shoulder width in 2D to scale depth consistently
    sh_width_2d = np.linalg.norm(body_clean[:, 11, :2] - body_clean[:, 12, :2], axis=1).mean()
    if sh_width_2d < 1e-3:
        sh_width_2d = 300.0
    
    # Convert body coordinates
    body_smplx = np.empty_like(body_clean)
    body_smplx[:, :, 0] = body_clean[:, :, 0]
    body_smplx[:, :, 1] = -body_clean[:, :, 1]
    body_smplx[:, :, 2] = -body_clean[:, :, 2] * sh_width_2d

    # Convert hand coordinates
    # Hand coordinates relative to wrist in pixel space:
    lh_smplx = np.empty_like(lh_clean)
    lh_smplx[:, :, 0] = lh_clean[:, :, 0]
    lh_smplx[:, :, 1] = -lh_clean[:, :, 1]
    lh_smplx[:, :, 2] = -lh_clean[:, :, 2] * sh_width_2d

    rh_smplx = np.empty_like(rh_clean)
    rh_smplx[:, :, 0] = rh_clean[:, :, 0]
    rh_smplx[:, :, 1] = -rh_clean[:, :, 1]
    rh_smplx[:, :, 2] = -rh_clean[:, :, 2] * sh_width_2d

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
# 3. SMPL-X SKELETON RETARGETER
# ==============================================================================

class SMPLXRetargeter:
    """
    Retargets cleaned MediaPipe 33-point body and 21-point left/right hands to SMPL-X.
    Calculates local joint rotations hierarchically using bone direction alignment.
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
            **layer_arg
        ).to(self.device)
        self.parents = self.model.parents.cpu().numpy()
        self.num_joints = len(self.parents)

        # Calculate rest pose joint locations from neutral template
        v_template = self.model.v_template.unsqueeze(0)  # [1, 10475, 3]
        J_regressor = self.model.J_regressor.unsqueeze(0)  # [1, 55, 10475]
        self.J_rest = torch.matmul(J_regressor, v_template)[0].cpu().numpy()  # [55, 3]

        self._build_rest_bone_vectors()

    def _build_rest_bone_vectors(self):
        """Precompute normalized rest-pose bone vectors for all joints."""
        self.rest_bones: Dict[str, np.ndarray] = {}

        J = self.J_rest
        # Body rest bones (parent -> child direction in rest pose)
        self.rest_bones["pelvis_up"] = normalize_vector(J[9] - J[0])            # spine3 - pelvis (+Y)
        self.rest_bones["pelvis_across"] = normalize_vector(J[1] - J[2])        # L_hip - R_hip (+X)
        self.rest_bones["spine1"] = normalize_vector(J[6] - J[3])               # spine2 - spine1 (+Y)
        self.rest_bones["spine2"] = normalize_vector(J[9] - J[6])               # spine3 - spine2 (+Y)
        self.rest_bones["spine3"] = normalize_vector(J[12] - J[9])              # neck - spine3 (+Y)
        self.rest_bones["neck"] = normalize_vector(J[15] - J[12])               # head - neck (+Y)
        
        # Left Arm
        self.rest_bones["l_collar"] = normalize_vector(J[16] - J[13])           # L_shoulder - L_collar (+X)
        self.rest_bones["l_shoulder"] = normalize_vector(J[18] - J[16])         # L_elbow - L_shoulder (+X)
        self.rest_bones["l_elbow"] = normalize_vector(J[20] - J[18])            # L_wrist - L_elbow (+X)
        self.rest_bones["l_wrist"] = normalize_vector(J[28] - J[20])            # L_middle1 - L_wrist (+X)

        # Right Arm
        self.rest_bones["r_collar"] = normalize_vector(J[17] - J[14])           # R_shoulder - R_collar (-X)
        self.rest_bones["r_shoulder"] = normalize_vector(J[19] - J[17])         # R_elbow - R_shoulder (-X)
        self.rest_bones["r_elbow"] = normalize_vector(J[21] - J[19])            # R_wrist - R_elbow (-X)
        self.rest_bones["r_wrist"] = normalize_vector(J[43] - J[21])            # R_middle1 - R_wrist (-X)

        # Legs
        self.rest_bones["l_hip"] = normalize_vector(J[4] - J[1])                # L_knee - L_hip (-Y)
        self.rest_bones["l_knee"] = normalize_vector(J[7] - J[4])               # L_ankle - L_knee (-Y)
        self.rest_bones["l_ankle"] = normalize_vector(J[10] - J[7])             # L_foot - L_ankle
        
        self.rest_bones["r_hip"] = normalize_vector(J[5] - J[2])                # R_knee - R_hip (-Y)
        self.rest_bones["r_knee"] = normalize_vector(J[8] - J[5])               # R_ankle - R_knee (-Y)
        self.rest_bones["r_ankle"] = normalize_vector(J[11] - J[8])             # R_foot - R_ankle

        # Hand full 3D rest frames
        lh_along = J[28] - J[20]
        lh_across = J[25] - J[31]
        lh_along = normalize_vector(lh_along)
        lh_across = lh_across - np.dot(lh_across, lh_along) * lh_along
        lh_across = normalize_vector(lh_across)
        lh_normal = normalize_vector(np.cross(lh_along, lh_across))
        self.rest_bones["lh_frame_along"] = lh_along
        self.rest_bones["lh_frame_across"] = lh_across
        self.rest_bones["lh_frame_normal"] = lh_normal

        rh_along = J[43] - J[21]
        rh_across = J[40] - J[46]
        rh_along = normalize_vector(rh_along)
        rh_across = rh_across - np.dot(rh_across, rh_along) * rh_along
        rh_across = normalize_vector(rh_across)
        rh_normal = normalize_vector(np.cross(rh_along, rh_across))
        self.rest_bones["rh_frame_along"] = rh_along
        self.rest_bones["rh_frame_across"] = rh_across
        self.rest_bones["rh_frame_normal"] = rh_normal

        # Left Hand Fingers (Index: 25-27, Middle: 28-30, Pinky: 31-33, Ring: 34-36, Thumb: 37-39)
        self.rest_bones["lh_index1"] = normalize_vector(J[26] - J[25])
        self.rest_bones["lh_index2"] = normalize_vector(J[27] - J[26])
        self.rest_bones["lh_index3"] = normalize_vector(J[27] - J[26])          # tip extension
        
        self.rest_bones["lh_middle1"] = normalize_vector(J[29] - J[28])
        self.rest_bones["lh_middle2"] = normalize_vector(J[30] - J[29])
        self.rest_bones["lh_middle3"] = normalize_vector(J[30] - J[29])

        self.rest_bones["lh_pinky1"] = normalize_vector(J[32] - J[31])
        self.rest_bones["lh_pinky2"] = normalize_vector(J[33] - J[32])
        self.rest_bones["lh_pinky3"] = normalize_vector(J[33] - J[32])

        self.rest_bones["lh_ring1"] = normalize_vector(J[35] - J[34])
        self.rest_bones["lh_ring2"] = normalize_vector(J[36] - J[35])
        self.rest_bones["lh_ring3"] = normalize_vector(J[36] - J[35])

        self.rest_bones["lh_thumb1"] = normalize_vector(J[38] - J[37])
        self.rest_bones["lh_thumb2"] = normalize_vector(J[39] - J[38])
        self.rest_bones["lh_thumb3"] = normalize_vector(J[39] - J[38])

        # Right Hand Fingers (Index: 40-42, Middle: 43-45, Pinky: 46-48, Ring: 49-51, Thumb: 52-54)
        self.rest_bones["rh_index1"] = normalize_vector(J[41] - J[40])
        self.rest_bones["rh_index2"] = normalize_vector(J[42] - J[41])
        self.rest_bones["rh_index3"] = normalize_vector(J[42] - J[41])

        self.rest_bones["rh_middle1"] = normalize_vector(J[44] - J[43])
        self.rest_bones["rh_middle2"] = normalize_vector(J[45] - J[44])
        self.rest_bones["rh_middle3"] = normalize_vector(J[45] - J[44])

        self.rest_bones["rh_pinky1"] = normalize_vector(J[47] - J[46])
        self.rest_bones["rh_pinky2"] = normalize_vector(J[48] - J[47])
        self.rest_bones["rh_pinky3"] = normalize_vector(J[48] - J[47])

        self.rest_bones["rh_ring1"] = normalize_vector(J[50] - J[49])
        self.rest_bones["rh_ring2"] = normalize_vector(J[51] - J[50])
        self.rest_bones["rh_ring3"] = normalize_vector(J[51] - J[50])

        self.rest_bones["rh_thumb1"] = normalize_vector(J[53] - J[52])
        self.rest_bones["rh_thumb2"] = normalize_vector(J[54] - J[53])
        self.rest_bones["rh_thumb3"] = normalize_vector(J[54] - J[53])

    def retarget_frame(
        self,
        body: np.ndarray,      # (33, 3) in SMPL-X coordinate space
        lh: np.ndarray,        # (21, 3) in SMPL-X coordinate space
        rh: np.ndarray         # (21, 3) in SMPL-X coordinate space
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculates SMPL-X pose parameters for a single frame:
        Returns:
            global_orient: (3,)
            body_pose: (63,)  [21 body joints * 3]
            left_hand_pose: (45,) [15 finger joints * 3]
            right_hand_pose: (45,) [15 finger joints * 3]
            transl: (3,)
        """
        # ======================================================================
        # 1. ROOT ORIENTATION & TORSO
        # ======================================================================
        # MediaPipe body landmark indices:
        # 0: nose, 11: L_sh, 12: R_sh, 13: L_elb, 14: R_elb, 15: L_wri, 16: R_wri
        # 23: L_hip, 24: R_hip, 25: L_knee, 26: R_knee, 27: L_ank, 28: R_ank, 31: L_foot, 32: R_foot

        mid_hip = (body[23] + body[24]) / 2.0
        mid_shoulder = (body[11] + body[12]) / 2.0

        target_torso_up = normalize_vector(mid_shoulder - mid_hip)
        target_torso_across = normalize_vector(body[23] - body[24]) # R_hip -> L_hip (+X)
        target_torso_fwd = normalize_vector(np.cross(target_torso_across, target_torso_up))
        # Re-orthonormalize across
        target_torso_across = normalize_vector(np.cross(target_torso_up, target_torso_fwd))

        # Pelvis global orientation matrix G_0: columns = [across, up, fwd]
        G_pelvis = np.column_stack([target_torso_across, target_torso_up, target_torso_fwd]).astype(np.float32)
        global_orient = matrix_to_axis_angle(G_pelvis)

        # Spine and Neck
        # Spine global rotations align with torso up
        G_spine1 = G_pelvis.copy()
        G_spine2 = G_pelvis.copy()
        G_spine3 = G_pelvis.copy()
        
        head_vec = normalize_vector(body[0] - mid_shoulder)
        R_neck_align = rotation_between_vectors(np.array([0.0, 1.0, 0.0]), head_vec)
        G_neck = R_neck_align @ G_spine3

        # ======================================================================
        # 2. LEFT ARM RETARGETING
        # ======================================================================
        # Target bone directions
        u_l_collar = normalize_vector(body[11] - mid_shoulder)
        u_l_upper_arm = normalize_vector(body[13] - body[11])
        u_l_forearm = normalize_vector(body[15] - body[13])

        G_l_collar = rotation_between_vectors(self.rest_bones["l_collar"], u_l_collar)
        G_l_shoulder = rotation_between_vectors(self.rest_bones["l_shoulder"], u_l_upper_arm)
        G_l_elbow = rotation_between_vectors(self.rest_bones["l_elbow"], u_l_forearm)

        # Left Wrist: use full 3D hand basis (along palm, across pinky->index, palm normal)
        # LH indices: 0: wrist, 5: index_mcp, 9: middle_mcp, 17: pinky_mcp
        lh_wrist = lh[0]
        lh_mid_mcp = lh[9]
        lh_idx_mcp = lh[5]
        lh_pnk_mcp = lh[17]

        lh_along = lh_mid_mcp - lh_wrist
        if np.linalg.norm(lh_along) > 1e-4:
            lh_along = normalize_vector(lh_along)
            lh_across = lh_idx_mcp - lh_pnk_mcp
            lh_across = lh_across - np.dot(lh_across, lh_along) * lh_along
            if np.linalg.norm(lh_across) > 1e-4:
                lh_across = normalize_vector(lh_across)
            else:
                lh_across = np.array([0.0, 0.0, 1.0], dtype=np.float32)
            lh_normal = normalize_vector(np.cross(lh_along, lh_across))

            F_target_lh = np.column_stack([lh_along, lh_across, lh_normal])
            # Rest frame for left hand
            F_rest_lh = np.column_stack([
                self.rest_bones["lh_frame_along"],
                self.rest_bones["lh_frame_across"],
                self.rest_bones["lh_frame_normal"]
            ])
            G_l_wrist = F_target_lh @ F_rest_lh.T
        else:
            G_l_wrist = rotation_between_vectors(self.rest_bones["l_wrist"], u_l_forearm)

        # ======================================================================
        # 3. RIGHT ARM RETARGETING
        # ======================================================================
        u_r_collar = normalize_vector(body[12] - mid_shoulder)
        u_r_upper_arm = normalize_vector(body[14] - body[12])
        u_r_forearm = normalize_vector(body[16] - body[14])

        G_r_collar = rotation_between_vectors(self.rest_bones["r_collar"], u_r_collar)
        G_r_shoulder = rotation_between_vectors(self.rest_bones["r_shoulder"], u_r_upper_arm)
        G_r_elbow = rotation_between_vectors(self.rest_bones["r_elbow"], u_r_forearm)

        # Right Wrist: use full 3D hand basis
        rh_wrist = rh[0]
        rh_mid_mcp = rh[9]
        rh_idx_mcp = rh[5]
        rh_pnk_mcp = rh[17]

        rh_along = rh_mid_mcp - rh_wrist
        if np.linalg.norm(rh_along) > 1e-4:
            rh_along = normalize_vector(rh_along)
            rh_across = rh_idx_mcp - rh_pnk_mcp
            rh_across = rh_across - np.dot(rh_across, rh_along) * rh_along
            if np.linalg.norm(rh_across) > 1e-4:
                rh_across = normalize_vector(rh_across)
            else:
                rh_across = np.array([0.0, 0.0, 1.0], dtype=np.float32)
            rh_normal = normalize_vector(np.cross(rh_along, rh_across))

            F_target_rh = np.column_stack([rh_along, rh_across, rh_normal])
            # Rest frame for right hand
            F_rest_rh = np.column_stack([
                self.rest_bones["rh_frame_along"],
                self.rest_bones["rh_frame_across"],
                self.rest_bones["rh_frame_normal"]
            ])
            G_r_wrist = F_target_rh @ F_rest_rh.T
        else:
            G_r_wrist = rotation_between_vectors(self.rest_bones["r_wrist"], u_r_forearm)

        # ======================================================================
        # 4. LEGS RETARGETING
        # ======================================================================
        u_l_thigh = normalize_vector(body[25] - body[23])
        u_l_shin = normalize_vector(body[27] - body[25])
        u_l_foot = normalize_vector(body[31] - body[27])

        G_l_hip = rotation_between_vectors(self.rest_bones["l_hip"], u_l_thigh)
        G_l_knee = rotation_between_vectors(self.rest_bones["l_knee"], u_l_shin)
        G_l_ankle = rotation_between_vectors(self.rest_bones["l_ankle"], u_l_foot)

        u_r_thigh = normalize_vector(body[26] - body[24])
        u_r_shin = normalize_vector(body[28] - body[26])
        u_r_foot = normalize_vector(body[32] - body[28])

        G_r_hip = rotation_between_vectors(self.rest_bones["r_hip"], u_r_thigh)
        G_r_knee = rotation_between_vectors(self.rest_bones["r_knee"], u_r_shin)
        G_r_ankle = rotation_between_vectors(self.rest_bones["r_ankle"], u_r_foot)

        # ======================================================================
        # 5. COMPUTE LOCAL BODY ROTATIONS (R = G_parent^T * G_child)
        # ======================================================================
        # 21 body joints order in SMPL-X:
        # 1: L_Hip, 2: R_Hip, 3: Spine_1, 4: L_Knee, 5: R_Knee, 6: Spine_2, 7: L_Ankle, 8: R_Ankle,
        # 9: Spine_3, 10: L_Foot, 11: R_Foot, 12: Neck, 13: L_Collar, 14: R_Collar, 15: Head,
        # 16: L_Shoulder, 17: R_Shoulder, 18: L_Elbow, 19: R_Elbow, 20: L_Wrist, 21: R_Wrist
        body_rots = np.zeros((21, 3), dtype=np.float32)

        # Hips (parent 0: pelvis)
        body_rots[0] = matrix_to_axis_angle(G_pelvis.T @ G_l_hip)        # 1: L_Hip
        body_rots[1] = matrix_to_axis_angle(G_pelvis.T @ G_r_hip)        # 2: R_Hip
        body_rots[2] = matrix_to_axis_angle(G_pelvis.T @ G_spine1)       # 3: Spine_1

        # Knees & Ankles
        body_rots[3] = matrix_to_axis_angle(G_l_hip.T @ G_l_knee)        # 4: L_Knee
        body_rots[4] = matrix_to_axis_angle(G_r_hip.T @ G_r_knee)        # 5: R_Knee
        body_rots[5] = matrix_to_axis_angle(G_spine1.T @ G_spine2)       # 6: Spine_2
        body_rots[6] = matrix_to_axis_angle(G_l_knee.T @ G_l_ankle)      # 7: L_Ankle
        body_rots[7] = matrix_to_axis_angle(G_r_knee.T @ G_r_ankle)      # 8: R_Ankle
        body_rots[8] = matrix_to_axis_angle(G_spine2.T @ G_spine3)       # 9: Spine_3
        body_rots[9] = np.zeros(3, dtype=np.float32)                      # 10: L_Foot
        body_rots[10] = np.zeros(3, dtype=np.float32)                     # 11: R_Foot

        # Neck & Collars (parent 9: Spine_3)
        body_rots[11] = matrix_to_axis_angle(G_spine3.T @ G_neck)        # 12: Neck
        body_rots[12] = matrix_to_axis_angle(G_spine3.T @ G_l_collar)    # 13: L_Collar
        body_rots[13] = matrix_to_axis_angle(G_spine3.T @ G_r_collar)    # 14: R_Collar
        body_rots[14] = np.zeros(3, dtype=np.float32)                     # 15: Head

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
        # 6. INDEPENDENT FINGER ARTICULATION RETARGETING (15 joints per hand)
        # ======================================================================
        # Left Hand Fingers (parent: G_l_wrist)
        # MediaPipe indices:
        # Thumb: 1, 2, 3, 4
        # Index: 5, 6, 7, 8
        # Middle: 9, 10, 11, 12
        # Ring: 13, 14, 15, 16
        # Pinky: 17, 18, 19, 20
        lh_rots = np.zeros((15, 3), dtype=np.float32)

        def retarget_finger(
            landmarks: np.ndarray,
            indices: Tuple[int, int, int, int],
            rest_keys: Tuple[str, str, str],
            parent_G: np.ndarray
        ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
            p0, p1, p2, p3 = indices
            # Bone directions
            u0 = normalize_vector(landmarks[p1] - landmarks[p0])
            u1 = normalize_vector(landmarks[p2] - landmarks[p1])
            u2 = normalize_vector(landmarks[p3] - landmarks[p2])

            G0 = rotation_between_vectors(self.rest_bones[rest_keys[0]], u0)
            G1 = rotation_between_vectors(self.rest_bones[rest_keys[1]], u1)
            G2 = rotation_between_vectors(self.rest_bones[rest_keys[2]], u2)

            r0 = matrix_to_axis_angle(parent_G.T @ G0)
            r1 = matrix_to_axis_angle(G0.T @ G1)
            r2 = matrix_to_axis_angle(G1.T @ G2)
            return r0, r1, r2

        # Index (0, 1, 2)
        lh_rots[0], lh_rots[1], lh_rots[2] = retarget_finger(
            lh, (5, 6, 7, 8), ("lh_index1", "lh_index2", "lh_index3"), G_l_wrist
        )
        # Middle (3, 4, 5)
        lh_rots[3], lh_rots[4], lh_rots[5] = retarget_finger(
            lh, (9, 10, 11, 12), ("lh_middle1", "lh_middle2", "lh_middle3"), G_l_wrist
        )
        # Pinky (6, 7, 8)
        lh_rots[6], lh_rots[7], lh_rots[8] = retarget_finger(
            lh, (17, 18, 19, 20), ("lh_pinky1", "lh_pinky2", "lh_pinky3"), G_l_wrist
        )
        # Ring (9, 10, 11)
        lh_rots[9], lh_rots[10], lh_rots[11] = retarget_finger(
            lh, (13, 14, 15, 16), ("lh_ring1", "lh_ring2", "lh_ring3"), G_l_wrist
        )
        # Thumb (12, 13, 14)
        lh_rots[12], lh_rots[13], lh_rots[14] = retarget_finger(
            lh, (1, 2, 3, 4), ("lh_thumb1", "lh_thumb2", "lh_thumb3"), G_l_wrist
        )
        left_hand_pose = lh_rots.flatten()

        # Right Hand Fingers (parent: G_r_wrist)
        rh_rots = np.zeros((15, 3), dtype=np.float32)
        # Index (0, 1, 2)
        rh_rots[0], rh_rots[1], rh_rots[2] = retarget_finger(
            rh, (5, 6, 7, 8), ("rh_index1", "rh_index2", "rh_index3"), G_r_wrist
        )
        # Middle (3, 4, 5)
        rh_rots[3], rh_rots[4], rh_rots[5] = retarget_finger(
            rh, (9, 10, 11, 12), ("rh_middle1", "rh_middle2", "rh_middle3"), G_r_wrist
        )
        # Pinky (6, 7, 8)
        rh_rots[6], rh_rots[7], rh_rots[8] = retarget_finger(
            rh, (17, 18, 19, 20), ("rh_pinky1", "rh_pinky2", "rh_pinky3"), G_r_wrist
        )
        # Ring (9, 10, 11)
        rh_rots[9], rh_rots[10], rh_rots[11] = retarget_finger(
            rh, (13, 14, 15, 16), ("rh_ring1", "rh_ring2", "rh_ring3"), G_r_wrist
        )
        # Thumb (12, 13, 14)
        rh_rots[12], rh_rots[13], rh_rots[14] = retarget_finger(
            rh, (1, 2, 3, 4), ("rh_thumb1", "rh_thumb2", "rh_thumb3"), G_r_wrist
        )
        right_hand_pose = rh_rots.flatten()

        # Translation: Root pelvis remains centered
        transl = np.zeros(3, dtype=np.float32)

        return global_orient, body_pose, left_hand_pose, right_hand_pose, transl

    def retarget_sequence(
        self,
        cleaned_data: Dict[str, Any],
        batch_size: int = 32
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Retargets all frames and runs SMPL-X forward pass to generate (F, 10475, 3) vertices.
        """
        frames = cleaned_data["frames"]
        body_seq = cleaned_data["body"]
        lh_seq = cleaned_data["left_hand"]
        rh_seq = cleaned_data["right_hand"]

        logger.info(f"Retargeting {frames} frames with full body and 2-hand finger articulation...")

        global_orients = []
        body_poses = []
        lh_poses = []
        rh_poses = []
        transls = []

        for i in range(frames):
            go, bp, lhp, rhp, tr = self.retarget_frame(body_seq[i], lh_seq[i], rh_seq[i])
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

        # Forward pass in batches
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

        vertices = np.concatenate(all_vertices, axis=0) # (frames, 10475, 3)

        # Diagnostics & metadata
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

        return vertices, metadata


# ==============================================================================
# 4. CONVERSION PIPELINE ENTRYPOINT
# ==============================================================================

def convert_bridgeconn_sample(
    npz_path: str,
    output_npy_path: Optional[str] = None,
    output_json_path: Optional[str] = None
) -> Tuple[str, str]:
    """
    Complete end-to-end pipeline:
    1. Loads sample_1.npz
    2. Cleans landmarks & normalizes coordinates
    3. Retargets body and hands to SMPL-X
    4. Evaluates SMPL-X forward pass
    5. Saves (frames, 10475, 3) .npy and metadata .json
    """
    cleaned = clean_and_preprocess_sample(npz_path)
    gloss = cleaned["gloss"]

    out_dir = os.path.join(BASE_DIR, "outputs", "npy")
    os.makedirs(out_dir, exist_ok=True)

    if output_npy_path is None:
        output_npy_path = os.path.join(out_dir, f"{gloss}.npy")
    if output_json_path is None:
        output_json_path = os.path.join(out_dir, f"{gloss}.json")

    retargeter = SMPLXRetargeter()
    vertices, metadata = retargeter.retarget_sequence(cleaned)

    # Save NPY
    np.save(output_npy_path, vertices)
    logger.info(f"Saved animation vertices to: {output_npy_path} (Shape: {vertices.shape}, Dtype: {vertices.dtype})")

    # Save JSON metadata
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
    logger.info(f"Saved animation metadata to: {output_json_path}")

    return output_npy_path, output_json_path


if __name__ == "__main__":
    test_npz = os.path.join(BASE_DIR, "bridgeconn_samples", "sample_1.npz")
    convert_bridgeconn_sample(test_npz)
