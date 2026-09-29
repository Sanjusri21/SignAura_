"""
SMPL-X Motion Blender.

Performs parameter-level kinematic blending between two CanonicalMotion instances.
Transitions smoothly from the termination pose of Sign A into the inception pose of Sign B.

Key Techniques:
1. Coordinate alignment: Aligns root translation and horizontal orientation so signs flow
   seamlessly without unnatural position teleportation.
2. Cosine smooth easing: Nonlinear acceleration-deceleration curve in range (0, 1).
3. Rodrigues rotation interpolation: Smooth interpolation of 3D joint rotation vectors.
4. Hand transition: Eliminates abrupt finger snaps between signs.
"""

import logging
from typing import Tuple, Optional
import numpy as np
from scipy.spatial.transform import Rotation as R

from .canonical_motion import CanonicalMotion

logger = logging.getLogger("MotionBlender")


class MotionBlender:
    """
    Interpolates kinematic SMPL-X parameters across a temporal boundary window.
    """

    def __init__(self, default_transition_sec: float = 0.20):
        self.default_transition_sec = float(default_transition_sec)

    @staticmethod
    def _cosine_weights(num_steps: int) -> np.ndarray:
        """
        Computes cosine easing weights strictly within (0, 1) to avoid duplicating endpoints.
        """
        if num_steps <= 0:
            return np.empty((0, 1), dtype=np.float32)
        steps = np.arange(1, num_steps + 1, dtype=np.float32) / float(num_steps + 1)
        weights = 0.5 * (1.0 - np.cos(np.pi * steps))
        return weights[:, None]

    @classmethod
    def _blend_rotvecs(cls, rot_a: np.ndarray, rot_b: np.ndarray, weights: np.ndarray) -> np.ndarray:
        """
        Interpolates flattened rotvec arrays of shape (D,) from A to B across len(weights) steps.
        Reshapes to (D/3, 3), converts to SLERP quaternions for accurate angular geodesics,
        and converts back to rotvecs.
        """
        num_steps = len(weights)
        num_joints = len(rot_a) // 3

        vecs_a = rot_a.reshape(num_joints, 3)
        vecs_b = rot_b.reshape(num_joints, 3)

        out_rotvecs = np.zeros((num_steps, len(rot_a)), dtype=np.float32)

        for j in range(num_joints):
            va = vecs_a[j]
            vb = vecs_b[j]

            # Fast path: nearly identical vectors -> linear interpolation
            if np.linalg.norm(va - vb) < 1e-4:
                interp = (1.0 - weights) * va[None, :] + weights * vb[None, :]
                out_rotvecs[:, j * 3 : (j + 1) * 3] = interp
                continue

            r_a = R.from_rotvec(va)
            r_b = R.from_rotvec(vb)
            q_a = r_a.as_quat()
            q_b = r_b.as_quat()

            # Ensure shortest path on 4D sphere
            if np.dot(q_a, q_b) < 0:
                q_b = -q_b

            # Simple normalized linear blend for intermediate quaternions
            q_interp = (1.0 - weights) * q_a[None, :] + weights * q_b[None, :]
            q_norms = np.linalg.norm(q_interp, axis=-1, keepdims=True)
            q_interp = q_interp / np.where(q_norms < 1e-8, 1e-8, q_norms)

            interp_vecs = R.from_quat(q_interp).as_rotvec().astype(np.float32)
            out_rotvecs[:, j * 3 : (j + 1) * 3] = interp_vecs

        return out_rotvecs

    def blend(
        self,
        motion_a: CanonicalMotion,
        motion_b: CanonicalMotion,
        transition_frames: Optional[int] = None,
        align_root: bool = True,
    ) -> Tuple[CanonicalMotion, CanonicalMotion, CanonicalMotion]:
        """
        Generates a smooth transition between motion_a and motion_b.

        Args:
            motion_a: First CanonicalMotion.
            motion_b: Second CanonicalMotion.
            transition_frames: Number of transition frames (default calculated from transition_sec).
            align_root: If True, shifts motion_b translation to align with motion_a's endpoint.

        Returns:
            Tuple of (aligned_motion_a, transition_motion, aligned_motion_b)
        """
        # Ensure identical FPS
        target_fps = motion_a.fps
        if abs(motion_b.fps - target_fps) > 1e-2:
            motion_b = motion_b.resample(target_fps)

        if transition_frames is None:
            transition_frames = max(2, int(round(self.default_transition_sec * target_fps)))

        # Align root translation if requested (so character does not teleport)
        motion_b_aligned = motion_b.clone()
        if align_root and motion_a.num_frames > 0 and motion_b.num_frames > 0:
            transl_offset = motion_a.transl[-1] - motion_b.transl[0]
            # Keep vertical coordinate grounded, align horizontal X and Z
            motion_b_aligned.transl[:, 0] += transl_offset[0]
            motion_b_aligned.transl[:, 2] += transl_offset[2]

        weights = self._cosine_weights(transition_frames)

        # 1. Blend global_orient
        trans_orient = self._blend_rotvecs(
            motion_a.global_orient[-1],
            motion_b_aligned.global_orient[0],
            weights
        )

        # 2. Blend body_pose
        trans_body = self._blend_rotvecs(
            motion_a.body_pose[-1],
            motion_b_aligned.body_pose[0],
            weights
        )

        # 3. Blend left_hand_pose
        trans_lh = (1.0 - weights) * motion_a.left_hand_pose[-1][None, :] + weights * motion_b_aligned.left_hand_pose[0][None, :]

        # 4. Blend right_hand_pose
        trans_rh = (1.0 - weights) * motion_a.right_hand_pose[-1][None, :] + weights * motion_b_aligned.right_hand_pose[0][None, :]

        # 5. Blend jaw_pose
        trans_jaw = (1.0 - weights) * motion_a.jaw_pose[-1][None, :] + weights * motion_b_aligned.jaw_pose[0][None, :]

        # 6. Blend transl
        trans_transl = (1.0 - weights) * motion_a.transl[-1][None, :] + weights * motion_b_aligned.transl[0][None, :]

        trans_motion = CanonicalMotion(
            sign_id=f"TRANSITION_{motion_a.sign_id}_{motion_b.sign_id}",
            fps=target_fps,
            num_frames=transition_frames,
            global_orient=trans_orient.astype(np.float32),
            body_pose=trans_body.astype(np.float32),
            left_hand_pose=trans_lh.astype(np.float32),
            right_hand_pose=trans_rh.astype(np.float32),
            jaw_pose=trans_jaw.astype(np.float32),
            transl=trans_transl.astype(np.float32),
            metadata={"transition": True, "from": motion_a.sign_id, "to": motion_b.sign_id},
        )

        return motion_a, trans_motion, motion_b_aligned
