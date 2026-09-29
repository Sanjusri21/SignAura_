"""
SMPL-X Forward Kinematic Body Model.

Evaluates SMPL-X forward kinematics on canonical pose parameters to produce
(T, 10475, 3) 3D surface mesh vertices and joint positions.
"""

import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, Union

import numpy as np
import torch

from app.motion.canonical_motion import CanonicalMotion

logger = logging.getLogger("SMPLXModel")


class SMPLXBodyModel:
    """
    Evaluates SMPL-X forward kinematics in PyTorch.
    """

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        device: Optional[str] = None
    ):
        base_dir = Path(__file__).resolve().parents[3]
        if model_path is None:
            model_path = base_dir / "SignAvatars" / "common" / "utils" / "human_model_files"
        self.model_path = Path(model_path)

        # Ensure SignAvatars is on sys.path for smplx imports
        signavatars_dir = str(base_dir / "SignAvatars")
        if signavatars_dir not in sys.path:
            sys.path.insert(0, signavatars_dir)

        try:
            from common.utils.smplx import smplx
        except ImportError:
            import smplx

        self.smplx_module = smplx
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))

        logger.info(f"[SMPL-X] Loading neutral SMPL-X body model from {self.model_path} onto {self.device}...")
        self.model = self.smplx_module.create(
            str(self.model_path),
            model_type="smplx",
            gender="neutral",
            use_pca=False,
            use_face_contour=False,
            flat_hand_mean=True,
            batch_size=1,
        ).to(self.device)
        self.model.eval()
        self.faces = self.model.faces
        logger.info(f"[SMPL-X] Model loaded successfully: {len(self.faces)} faces")

    def forward(
        self,
        motion: Union[CanonicalMotion, Dict[str, Any]],
        batch_size: int = 32
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Runs batched forward pass on a CanonicalMotion or parameter dictionary.

        Returns:
            vertices: (T, 10475, 3) float32
            joints: (T, J, 3) float32
        """
        if isinstance(motion, CanonicalMotion):
            go = motion.global_orient
            bp = motion.body_pose
            lhp = motion.left_hand_pose
            rhp = motion.right_hand_pose
            jaw = motion.jaw_pose
            transl = motion.transl
            num_frames = motion.num_frames
            sign_id = motion.sign_id
        else:
            go = np.asarray(motion["global_orient"], dtype=np.float32)
            bp = np.asarray(motion["body_pose"], dtype=np.float32)
            lhp = np.asarray(motion.get("left_hand_pose", np.zeros((len(go), 45))), dtype=np.float32)
            rhp = np.asarray(motion.get("right_hand_pose", np.zeros((len(go), 45))), dtype=np.float32)
            jaw = np.asarray(motion.get("jaw_pose", np.zeros((len(go), 3))), dtype=np.float32)
            transl = np.asarray(motion.get("transl", np.zeros((len(go), 3))), dtype=np.float32)
            num_frames = len(go)
            sign_id = motion.get("sign_id", "ANONYMOUS")

        logger.info(f"[SMPL-X] Forward pass for '{sign_id}' ({num_frames} frames)...")

        all_verts = []
        all_joints = []

        with torch.no_grad():
            for i in range(0, num_frames, batch_size):
                end_i = min(i + batch_size, num_frames)
                b_size = end_i - i

                t_go = torch.tensor(go[i:end_i], dtype=torch.float32, device=self.device)
                t_bp = torch.tensor(bp[i:end_i], dtype=torch.float32, device=self.device)
                t_lhp = torch.tensor(lhp[i:end_i], dtype=torch.float32, device=self.device)
                t_rhp = torch.tensor(rhp[i:end_i], dtype=torch.float32, device=self.device)
                t_jaw = torch.tensor(jaw[i:end_i], dtype=torch.float32, device=self.device)
                t_transl = torch.tensor(transl[i:end_i], dtype=torch.float32, device=self.device)

                t_betas = torch.zeros((b_size, 10), dtype=torch.float32, device=self.device)
                t_expr = torch.zeros((b_size, 10), dtype=torch.float32, device=self.device)
                t_leye = torch.zeros((b_size, 3), dtype=torch.float32, device=self.device)
                t_reye = torch.zeros((b_size, 3), dtype=torch.float32, device=self.device)

                output = self.model(
                    global_orient=t_go,
                    body_pose=t_bp,
                    left_hand_pose=t_lhp,
                    right_hand_pose=t_rhp,
                    transl=t_transl,
                    jaw_pose=t_jaw,
                    betas=t_betas,
                    expression=t_expr,
                    leye_pose=t_leye,
                    reye_pose=t_reye,
                    return_verts=True,
                )

                verts_batch = output.vertices.detach().cpu().numpy().astype(np.float32)
                joints_batch = output.joints.detach().cpu().numpy().astype(np.float32)

                all_verts.append(verts_batch)
                all_joints.append(joints_batch)

        vertices = np.concatenate(all_verts, axis=0)
        joints = np.concatenate(all_joints, axis=0)

        logger.info(f"[SMPL-X] Forward pass completed: vertices shape {vertices.shape}")
        return vertices, joints


_default_smplx_model: Optional[SMPLXBodyModel] = None


def get_smplx_model() -> SMPLXBodyModel:
    """Returns singleton SMPLXBodyModel instance."""
    global _default_smplx_model
    if _default_smplx_model is None:
        _default_smplx_model = SMPLXBodyModel()
    return _default_smplx_model
