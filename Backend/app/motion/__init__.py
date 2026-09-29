"""
Canonical SMPL-X Motion Architecture for SignAura.
Modules:
- canonical_motion: CanonicalMotion representation (SMPL-X pose parameters)
- motion_database: Standard API to retrieve, list, save, and manage motions
- motion_loader: Filesystem and format loader for CanonicalMotion
- motion_validator: Multi-point tensor and parameter verification
- motion_blender: Smooth parameter-level interpolation and transition
- motion_sequencer: Continuous SMPL-X multi-sign sequence assembler
- text_to_motion: Text-to-motion extensible model interface
"""

from .canonical_motion import CanonicalMotion
from .motion_database import (
    MotionDatabase,
    get_motion,
    list_available_signs,
    validate_motion,
    save_motion,
    load_motion,
    get_motion_database,
)
from .motion_loader import MotionLoader
from .motion_validator import validate_motion as validate_motion_func
from .motion_blender import MotionBlender
from .motion_sequencer import MotionSequencer
from .text_to_motion import TextToSMPLXModelBase, DefaultTextToMotion, generate_motion

__all__ = [
    "CanonicalMotion",
    "MotionDatabase",
    "MotionLoader",
    "MotionBlender",
    "MotionSequencer",
    "TextToSMPLXModelBase",
    "DefaultTextToMotion",
    "get_motion",
    "list_available_signs",
    "validate_motion",
    "save_motion",
    "load_motion",
    "generate_motion",
    "get_motion_database",
]
