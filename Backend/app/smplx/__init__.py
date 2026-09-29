"""
SMPL-X Body Model and 3D Avatar Rendering Subsystem.
Modules:
- model: SMPLXBodyModel wrapper for forward kinematics
- renderer: SMPLXRenderer for offscreen 3D visualization and video/image/GIF export
"""

from .model import SMPLXBodyModel, get_smplx_model
from .renderer import SMPLXRenderer

__all__ = ["SMPLXBodyModel", "SMPLXRenderer", "get_smplx_model"]
