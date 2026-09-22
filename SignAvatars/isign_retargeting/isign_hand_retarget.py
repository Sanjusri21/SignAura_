"""
Isolated Hand Retargeter for iSign Hand Landmarks to SMPL-X.
Re-anchors local hand landmarks to retargeted body wrist,
builds orthonormal palm coordinate frames,
computes hierarchical finger joint rotations,
and outputs 45-dim left_hand_pose and right_hand_pose.
"""

from typing import Dict, Any, Tuple, Optional
import numpy as np
from scipy.spatial.transform import Rotation as R
from .isign_coordinate_adapter import safe_normalize
from .isign_body_retarget import shortest_arc_rotation, exponential_moving_average_rotvec


# MediaPipe Hand Landmarks indices (21 points)
# 0: Wrist
# 1: Thumb CMC, 2: Thumb MCP, 3: Thumb IP, 4: Thumb Tip
# 5: Index MCP, 6: Index PIP, 7: Index DIP, 8: Index Tip
# 9: Middle MCP, 10: Middle PIP, 11: Middle DIP, 12: Middle Tip
# 13: Ring MCP, 14: Ring PIP, 15: Ring DIP, 16: Ring Tip
# 17: Pinky MCP, 18: Pinky PIP, 19: Pinky DIP, 20: Pinky Tip


class ISignHandRetargeter:
    """
    Retargets 21-point local hand landmarks into SMPL-X hand pose parameters.
    SMPL-X Hand Pose structure: 15 joints * 3 axis-angle = 45 floats per hand.
    Joint Order: Index (1,2,3), Middle (1,2,3), Pinky (1,2,3), Ring (1,2,3), Thumb (1,2,3).
    """

    def __init__(self):
        pass

    def build_palm_frame(self, hand_pts: np.ndarray, is_left: bool) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Builds an orthonormal 3D coordinate frame for the palm.
        hand_pts: (21, 3)
        Returns: (u_along, u_across, u_normal) unit vectors.
        """
        if hand_pts is None or np.isnan(hand_pts).any():
            if is_left:
                return np.array([1.0, 0.0, 0.0], dtype=np.float32), np.array([0.0, 1.0, 0.0], dtype=np.float32), np.array([0.0, 0.0, 1.0], dtype=np.float32)
            else:
                return np.array([-1.0, 0.0, 0.0], dtype=np.float32), np.array([0.0, 1.0, 0.0], dtype=np.float32), np.array([0.0, 0.0, -1.0], dtype=np.float32)

        w = hand_pts[0]
        i_mcp = hand_pts[5]
        m_mcp = hand_pts[9]
        p_mcp = hand_pts[17]

        d_along = m_mcp - w
        d_across = i_mcp - p_mcp
        if np.linalg.norm(d_along) < 1e-4 or np.linalg.norm(d_across) < 1e-4:
            if is_left:
                return np.array([1.0, 0.0, 0.0], dtype=np.float32), np.array([0.0, 1.0, 0.0], dtype=np.float32), np.array([0.0, 0.0, 1.0], dtype=np.float32)
            else:
                return np.array([-1.0, 0.0, 0.0], dtype=np.float32), np.array([0.0, 1.0, 0.0], dtype=np.float32), np.array([0.0, 0.0, -1.0], dtype=np.float32)

        # Along axis: wrist to middle MCP
        u_along = safe_normalize(d_along)

        # Across axis: index MCP to pinky MCP
        u_across = safe_normalize(d_across)

        # Normal axis via right-handed cross product
        if is_left:
            # For left hand, dorsal normal = across x along
            u_normal = safe_normalize(np.cross(u_across, u_along))
        else:
            # For right hand, dorsal normal = along x across
            u_normal = safe_normalize(np.cross(u_along, u_across))

        # Re-orthonormalize across to ensure strict det = +1
        if is_left:
            u_across = safe_normalize(np.cross(u_along, u_normal))
        else:
            u_across = safe_normalize(np.cross(u_normal, u_along))

        return u_along, u_across, u_normal

    def retarget_single_hand(
        self,
        hand_pts: np.ndarray,
        is_left: bool
    ) -> np.ndarray:
        """
        Retargets a single frame of 21 hand landmarks to 45 SMPL-X hand pose parameters.
        Returns: (45,) float32 axis-angle array.
        """
        hand_pose = np.zeros(45, dtype=np.float32)
        if hand_pts is None or np.isnan(hand_pts).any():
            return hand_pose

        span = np.ptp(hand_pts, axis=0)
        if np.max(span) < 1e-3:
            return hand_pose

        # Build local palm basis
        u_along, u_across, u_normal = self.build_palm_frame(hand_pts, is_left)
        R_palm = np.column_stack([u_along, u_across, u_normal]).astype(np.float32)
        R_palm_inv = R_palm.T

        # Rest finger extension vector in canonical SMPL-X flat hand:
        # Left hand extends along +X, Right hand extends along -X
        REST_EXTEND = np.array([1.0, 0.0, 0.0], dtype=np.float32) if is_left else np.array([-1.0, 0.0, 0.0], dtype=np.float32)

        # Finger definitions: list of (joint_start_idx in 45-vec, [mcp, pip, dip, tip])
        # SMPL-X Order: Index, Middle, Pinky, Ring, Thumb
        finger_defs = [
            (0, [5, 6, 7, 8]),    # Index (joints 0, 1, 2)
            (9, [9, 10, 11, 12]), # Middle (joints 3, 4, 5)
            (18, [17, 18, 19, 20]), # Pinky (joints 6, 7, 8)
            (27, [13, 14, 15, 16]), # Ring (joints 9, 10, 11)
            (36, [1, 2, 3, 4]),     # Thumb (joints 12, 13, 14)
        ]

        for out_offset, joint_indices in finger_defs:
            p_base = hand_pts[joint_indices[0]]
            p_pip = hand_pts[joint_indices[1]]
            p_dip = hand_pts[joint_indices[2]]
            p_tip = hand_pts[joint_indices[3]]

            # Segment 1: Base to PIP
            dir_seg1_world = safe_normalize(p_pip - p_base)
            dir_seg1_palm = np.matmul(R_palm_inv, dir_seg1_world)
            R_joint1 = shortest_arc_rotation(REST_EXTEND, dir_seg1_palm)

            # Segment 2: PIP to DIP (in Segment 1 local frame)
            dir_seg2_world = safe_normalize(p_dip - p_pip)
            dir_seg2_palm = np.matmul(R_palm_inv, dir_seg2_world)
            dir_seg2_local = np.matmul(R_joint1.T, dir_seg2_palm)
            R_joint2 = shortest_arc_rotation(REST_EXTEND, dir_seg2_local)

            # Segment 3: DIP to Tip (in Segment 2 local frame)
            dir_seg3_world = safe_normalize(p_tip - p_dip)
            dir_seg3_palm = np.matmul(R_palm_inv, dir_seg3_world)
            dir_seg3_local = np.matmul(R_joint2.T, np.matmul(R_joint1.T, dir_seg3_palm))
            R_joint3 = shortest_arc_rotation(REST_EXTEND, dir_seg3_local)

            # Assign axis-angle vectors with physiological limit clamping (max 1.92 rad ~ 110 deg per joint)
            hand_pose[out_offset : out_offset + 3] = self._clamp_rotvec(R_joint1, max_angle=1.92)
            hand_pose[out_offset + 3 : out_offset + 6] = self._clamp_rotvec(R_joint2, max_angle=1.92)
            hand_pose[out_offset + 6 : out_offset + 9] = self._clamp_rotvec(R_joint3, max_angle=1.92)

        return hand_pose

    def _clamp_rotvec(self, r_mat: np.ndarray, max_angle: float = 1.92) -> np.ndarray:
        """Clamps axis-angle rotation vector to physiological maximum angle (~110 deg)."""
        rotvec = R.from_matrix(r_mat).as_rotvec().astype(np.float32)
        angle = float(np.linalg.norm(rotvec))
        if angle > max_angle and angle > 1e-6:
            rotvec = rotvec * (max_angle / angle)
        return rotvec

    def retarget_sequence(
        self,
        left_hand: np.ndarray,
        right_hand: np.ndarray,
        smooth: bool = True,
        smoothing_alpha: float = 0.85
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Retargets left and right hand sequences over all frames.
        Inputs: left_hand (T, 21, 3), right_hand (T, 21, 3)
        Returns:
          - left_hand_pose: (T, 45)
          - right_hand_pose: (T, 45)
          - diagnostics: velocity and flexion metrics
        """
        T = left_hand.shape[0]
        lh_pose = np.zeros((T, 45), dtype=np.float32)
        rh_pose = np.zeros((T, 45), dtype=np.float32)

        for t in range(T):
            lh_pose[t] = self.retarget_single_hand(left_hand[t], is_left=True)
            rh_pose[t] = self.retarget_single_hand(right_hand[t], is_left=False)

        # Forward fill tracking dropouts to preserve continuity
        for t in range(1, T):
            if np.all(lh_pose[t] == 0) and not np.all(lh_pose[t-1] == 0):
                lh_pose[t] = lh_pose[t-1]
            if np.all(rh_pose[t] == 0) and not np.all(rh_pose[t-1] == 0):
                rh_pose[t] = rh_pose[t-1]

        vel_lh_raw = float(np.mean(np.linalg.norm(np.diff(lh_pose, axis=0), axis=-1)))
        vel_rh_raw = float(np.mean(np.linalg.norm(np.diff(rh_pose, axis=0), axis=-1)))

        if smooth:
            lh_pose = exponential_moving_average_rotvec(lh_pose, alpha=smoothing_alpha)
            rh_pose = exponential_moving_average_rotvec(rh_pose, alpha=smoothing_alpha)

        vel_lh_filt = float(np.mean(np.linalg.norm(np.diff(lh_pose, axis=0), axis=-1)))
        vel_rh_filt = float(np.mean(np.linalg.norm(np.diff(rh_pose, axis=0), axis=-1)))

        diagnostics = {
            "left_hand_mean_rot_vel_raw": vel_lh_raw,
            "left_hand_mean_rot_vel_filtered": vel_lh_filt,
            "right_hand_mean_rot_vel_raw": vel_rh_raw,
            "right_hand_mean_rot_vel_filtered": vel_rh_filt,
            "smoothing_alpha": smoothing_alpha if smooth else 1.0,
            "max_left_finger_rot_angle": float(np.max(np.abs(lh_pose))),
            "max_right_finger_rot_angle": float(np.max(np.abs(rh_pose))),
        }

        return lh_pose, rh_pose, diagnostics
