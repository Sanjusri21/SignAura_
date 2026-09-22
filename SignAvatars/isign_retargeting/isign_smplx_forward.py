"""
Isolated SMPL-X Forward Kinematics Evaluation.
Takes retargeted pose parameters, evaluates neutral SMPL-X model,
and outputs 3D mesh vertices (T, 10475, 3) and joints.
"""

from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import numpy as np
import torch
import sys
# Ensure SignAvatars directory is on sys.path for common.utils.smplx
_signavatars_dir = str(Path(__file__).resolve().parent.parent)
if _signavatars_dir not in sys.path:
    sys.path.insert(0, _signavatars_dir)

try:
    from common.utils.smplx import smplx
except ImportError:
    try:
        from SignAvatars.common.utils.smplx import smplx
    except ImportError:
        import smplx


class ISignSMPLXForwardPass:
    """
    Evaluates the neutral SMPL-X forward pass using PyTorch.
    Produces baked (T, 10475, 3) float32 vertex trajectories.
    """

    def __init__(self, human_model_path: Optional[str | Path] = None, device: Optional[str] = None):
        if human_model_path is None:
            base = Path(__file__).resolve().parent.parent / "common" / "utils" / "human_model_files"
            human_model_path = base
        else:
            human_model_path = Path(human_model_path)

        self.human_model_path = str(human_model_path)
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))

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
            self.human_model_path,
            model_type="smplx",
            gender="neutral",
            use_pca=False,
            use_face_contour=False,
            flat_hand_mean=True,
            batch_size=1,
        ).to(self.device)
        self.model.eval()

    def forward(
        self,
        global_orient: np.ndarray,
        body_pose: np.ndarray,
        left_hand_pose: np.ndarray,
        right_hand_pose: np.ndarray,
        transl: Optional[np.ndarray] = None,
        batch_size: int = 64
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Executes SMPL-X forward pass in batches to avoid GPU/CPU memory spikes.
        Inputs:
          - global_orient: (T, 3)
          - body_pose: (T, 63)
          - left_hand_pose: (T, 45)
          - right_hand_pose: (T, 45)
          - transl: (T, 3) optional, defaults to zero
        Returns:
          - vertices: (T, 10475, 3) float32
          - joints: (T, J, 3) float32
        """
        T = global_orient.shape[0]
        if transl is None:
            transl = np.zeros((T, 3), dtype=np.float32)

        all_verts = []
        all_joints = []

        with torch.no_grad():
            for i in range(0, T, batch_size):
                end_i = min(i + batch_size, T)
                B = end_i - i
                
                t_go = torch.tensor(global_orient[i:end_i], dtype=torch.float32, device=self.device)
                t_bp = torch.tensor(body_pose[i:end_i], dtype=torch.float32, device=self.device)
                t_lh = torch.tensor(left_hand_pose[i:end_i], dtype=torch.float32, device=self.device)
                t_rh = torch.tensor(right_hand_pose[i:end_i], dtype=torch.float32, device=self.device)
                t_tr = torch.tensor(transl[i:end_i], dtype=torch.float32, device=self.device)

                output = self.model(
                    global_orient=t_go,
                    body_pose=t_bp,
                    left_hand_pose=t_lh,
                    right_hand_pose=t_rh,
                    transl=t_tr,
                    jaw_pose=torch.zeros((B, 3), dtype=torch.float32, device=self.device),
                    leye_pose=torch.zeros((B, 3), dtype=torch.float32, device=self.device),
                    reye_pose=torch.zeros((B, 3), dtype=torch.float32, device=self.device),
                    expression=torch.zeros((B, 10), dtype=torch.float32, device=self.device),
                    betas=torch.zeros((B, 10), dtype=torch.float32, device=self.device),
                    return_verts=True
                )

                all_verts.append(output.vertices.cpu().numpy())
                all_joints.append(output.joints.cpu().numpy())

        vertices = np.concatenate(all_verts, axis=0).astype(np.float32)
        joints = np.concatenate(all_joints, axis=0).astype(np.float32)

        return vertices, joints
