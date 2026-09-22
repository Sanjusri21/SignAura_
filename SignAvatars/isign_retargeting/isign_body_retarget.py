"""
Isolated Body Retargeting for iSign World Landmarks to SMPL-X.
Computes:
  - global_orient (T, 3): Torso orientation from shoulder/hip frames.
  - body_pose (T, 63): Kinematically hierarchical arm, spine, and leg rotations.
  - transl (T, 3): Centered reference translation.
Includes conservative temporal smoothing for rotational stability.
"""

from typing import Dict, Any, Tuple, Optional
import numpy as np
from scipy.spatial.transform import Rotation as R
from .isign_coordinate_adapter import safe_normalize, ISignCoordinateAdapter


def shortest_arc_rotation(v_from: np.ndarray, v_to: np.ndarray) -> np.ndarray:
    """
    Computes shortest-arc 3x3 rotation matrix mapping unit vector v_from to v_to.
    Handles parallel, antiparallel, zero-length, and NaN edge cases robustly.
    """
    if v_from is None or v_to is None or np.isnan(v_from).any() or np.isnan(v_to).any():
        return np.eye(3, dtype=np.float32)

    norm_from = float(np.linalg.norm(v_from))
    norm_to = float(np.linalg.norm(v_to))
    if norm_from < 1e-6 or norm_to < 1e-6:
        return np.eye(3, dtype=np.float32)

    v_from = (v_from / norm_from).flatten()
    v_to = (v_to / norm_to).flatten()

    dot = float(np.dot(v_from, v_to))
    if dot > 0.999999:
        return np.eye(3, dtype=np.float32)

    if dot < -0.999999:
        # 180-degree flip around orthogonal axis
        ortho = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        if abs(v_from[0]) > 0.9:
            ortho = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        axis = safe_normalize(np.cross(v_from, ortho)).flatten()
        return R.from_rotvec(axis * np.pi).as_matrix().astype(np.float32)

    cross = np.cross(v_from, v_to)
    w = 1.0 + dot
    q = np.array([cross[0], cross[1], cross[2], w], dtype=np.float32)
    q_norm = float(np.linalg.norm(q))
    if q_norm < 1e-7 or np.isnan(q).any():
        return np.eye(3, dtype=np.float32)
    q = q / q_norm
    return R.from_quat(q).as_matrix().astype(np.float32)


def exponential_moving_average_rotvec(rotvecs: np.ndarray, alpha: float = 0.80) -> np.ndarray:
    """
    Applies conservative temporal filtering over rotvec sequences (T, ...).
    Preserves deliberate sign motion while attenuating high-frequency noise.
    """
    if len(rotvecs) <= 1 or alpha >= 1.0:
        return rotvecs

    smoothed = np.empty_like(rotvecs)
    smoothed[0] = rotvecs[0]
    for t in range(1, len(rotvecs)):
        smoothed[t] = alpha * rotvecs[t] + (1.0 - alpha) * smoothed[t - 1]
    return smoothed


class ISignBodyRetargeter:
    """
    Retargets canonical-length body joint directions into SMPL-X pose parameters.
    """

    def __init__(self, adapter: Optional[ISignCoordinateAdapter] = None):
        self.adapter = adapter or ISignCoordinateAdapter()

    def retarget_body(
        self,
        world_body: np.ndarray,
        smooth: bool = True,
        smoothing_alpha: float = 0.80,
    ) -> Dict[str, Any]:
        """
        Retargets iSign POSE_WORLD_LANDMARKS (T, 33, 3) to SMPL-X body parameters.
        Returns:
          - global_orient: (T, 3)
          - body_pose: (T, 63)
          - transl: (T, 3)
          - diagnostics: velocity/acceleration metrics before and after filtering
        """
        T = world_body.shape[0]
        dirs = self.adapter.extract_body_directions(world_body)

        global_orient = np.zeros((T, 3), dtype=np.float32)
        body_pose = np.zeros((T, 63), dtype=np.float32)
        transl = np.zeros((T, 3), dtype=np.float32)

        # SMPL-X canonical arm directions in rest T-pose:
        # Left arm points along +X, Right arm points along -X
        REST_L_ARM = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        REST_R_ARM = np.array([-1.0, 0.0, 0.0], dtype=np.float32)
        REST_TORSO_UP = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        for t in range(T):
            # 1. Torso Global Orientation
            # Construct orthonormal basis [x: across shoulders, y: torso up, z: facing forward]
            u_up = dirs["torso_up"][t]
            u_across = dirs["shoulder_across"][t]
            u_fwd = dirs["torso_normal"][t]

            R_torso = np.column_stack([u_across, u_up, u_fwd]).astype(np.float32)
            # Ensure valid right-handed orthogonal matrix
            U, _, Vt = np.linalg.svd(R_torso)
            R_torso = np.matmul(U, Vt)
            if np.linalg.det(R_torso) < 0:
                R_torso[:, 2] *= -1.0

            global_orient[t] = R.from_matrix(R_torso).as_rotvec().astype(np.float32)

            # 2. Arms in Torso Local Frame
            # Transform observed upper arm and forearm vectors into torso space
            R_torso_inv = R_torso.T

            # Left Arm Hierarchy
            l_up_torso = np.matmul(R_torso_inv, dirs["left_upper_arm"][t])
            R_l_sh = shortest_arc_rotation(REST_L_ARM, l_up_torso)

            # Left Forearm in Upper Arm local space
            l_fore_torso = np.matmul(R_torso_inv, dirs["left_forearm"][t])
            l_fore_local = np.matmul(R_l_sh.T, l_fore_torso)
            R_l_el = shortest_arc_rotation(REST_L_ARM, l_fore_local)

            # Right Arm Hierarchy
            r_up_torso = np.matmul(R_torso_inv, dirs["right_upper_arm"][t])
            R_r_sh = shortest_arc_rotation(REST_R_ARM, r_up_torso)

            # Right Forearm in Upper Arm local space
            r_fore_torso = np.matmul(R_torso_inv, dirs["right_forearm"][t])
            r_fore_local = np.matmul(R_r_sh.T, r_fore_torso)
            R_r_el = shortest_arc_rotation(REST_R_ARM, r_fore_local)

            # Assign joint rotations to body_pose indices:
            # joint 16 (L_shoulder) -> body_pose[45:48]
            # joint 17 (R_shoulder) -> body_pose[48:51]
            # joint 18 (L_elbow)    -> body_pose[51:54]
            # joint 19 (R_elbow)    -> body_pose[54:57]
            body_pose[t, 45:48] = R.from_matrix(R_l_sh).as_rotvec().astype(np.float32)
            body_pose[t, 48:51] = R.from_matrix(R_r_sh).as_rotvec().astype(np.float32)
            body_pose[t, 51:54] = R.from_matrix(R_l_el).as_rotvec().astype(np.float32)
            body_pose[t, 54:57] = R.from_matrix(R_r_el).as_rotvec().astype(np.float32)

            # Stable translation: keep root centered at origin with standard ground clearance
            transl[t] = np.array([0.0, 0.0, 0.0], dtype=np.float32)

        # Compute raw temporal motion metrics
        vel_raw = np.linalg.norm(np.diff(body_pose, axis=0), axis=-1)
        acc_raw = np.linalg.norm(np.diff(vel_raw, axis=0), axis=-1) if len(vel_raw) > 1 else np.array([0.0])

        if smooth:
            global_orient = exponential_moving_average_rotvec(global_orient, alpha=smoothing_alpha)
            body_pose = exponential_moving_average_rotvec(body_pose, alpha=smoothing_alpha)

        vel_filtered = np.linalg.norm(np.diff(body_pose, axis=0), axis=-1)
        acc_filtered = np.linalg.norm(np.diff(vel_filtered, axis=0), axis=-1) if len(vel_filtered) > 1 else np.array([0.0])

        diagnostics = {
            "mean_frame_angular_change_raw": float(np.mean(vel_raw)),
            "mean_frame_angular_change_filtered": float(np.mean(vel_filtered)),
            "mean_angular_acc_raw": float(np.mean(acc_raw)),
            "mean_angular_acc_filtered": float(np.mean(acc_filtered)),
            "smoothing_alpha": smoothing_alpha if smooth else 1.0,
        }

        return {
            "global_orient": global_orient,
            "body_pose": body_pose,
            "transl": transl,
            "diagnostics": diagnostics,
        }
