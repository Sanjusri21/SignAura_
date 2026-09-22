"""
Isolated iSign to SMPL-X Research Prototype Package.
Provides mathematically grounded, isolated adapters for retargeting genuine iSign poses to SMPL-X.
DO NOT IMPORT INTO BRIDGECONN PRODUCTION PIPELINE.
"""

from .isign_pose_loader import load_isign_pose, ISignPoseData
from .isign_coordinate_adapter import ISignCoordinateAdapter
from .isign_body_retarget import ISignBodyRetargeter
from .isign_hand_retarget import ISignHandRetargeter
from .isign_smplx_forward import ISignSMPLXForwardPass

__all__ = [
    "load_isign_pose",
    "ISignPoseData",
    "ISignCoordinateAdapter",
    "ISignBodyRetargeter",
    "ISignHandRetargeter",
    "ISignSMPLXForwardPass",
]
