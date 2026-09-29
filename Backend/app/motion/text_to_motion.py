"""
Future Text-to-Motion Model Interface.

Defines the pluggable architectural contract for future deep generative
Text-to-SMPL-X / Gloss-to-SMPL-X motion synthesis models.

Pipeline:
Gloss / Text -> Text-to-SMPL-X Motion Model -> Canonical SMPL-X Pose Parameters
"""

import abc
import logging
from typing import List, Optional, Union, Dict, Any

from .canonical_motion import CanonicalMotion
from .motion_database import get_motion_database, MotionDatabase

logger = logging.getLogger("TextToMotion")


class TextToSMPLXModelBase(abc.ABC):
    """
    Abstract interface for future text/gloss-to-SMPL-X generative models.
    """

    @abc.abstractmethod
    def generate_motion(self, query: Union[str, List[str]]) -> Optional[CanonicalMotion]:
        """
        Synthesizes a CanonicalMotion from text or a gloss sequence.
        """
        pass


class DefaultTextToMotion(TextToSMPLXModelBase):
    """
    Default reference implementation.
    Falls back to retrieval from SignMotionDB or returns NOT_IMPLEMENTED for generative synthesis.
    """

    def __init__(self, motion_db: Optional[MotionDatabase] = None):
        self.motion_db = motion_db or get_motion_database()

    def generate_motion(self, query: Union[str, List[str]]) -> Optional[CanonicalMotion]:
        """
        Attempts retrieval fallback; if not found, reports NOT_IMPLEMENTED status.
        """
        if isinstance(query, str):
            glosses = [query.strip().upper()]
        else:
            glosses = [g.strip().upper() for g in query if g.strip()]

        if not glosses:
            return None

        # Check if single sign exists in SignMotionDB
        if len(glosses) == 1:
            motion = self.motion_db.get_motion(glosses[0])
            if motion is not None:
                logger.info(f"[SMPL-X] Retrieved existing motion for '{glosses[0]}'")
                return motion

        logger.info(
            f"[SMPL-X] Text-to-motion generative model for '{query}': NOT_IMPLEMENTED "
            f"(Generative synthesis model will be plugged into this interface)"
        )
        return None


_default_generator = DefaultTextToMotion()


def generate_motion(gloss_sequence: Union[str, List[str]]) -> Optional[CanonicalMotion]:
    """Top-level generative motion synthesis function."""
    return _default_generator.generate_motion(gloss_sequence)
