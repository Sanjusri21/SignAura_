"""
SMPL-X Motion Database Service.

Provides a unified, thread-safe interface for managing and accessing the canonical
isolated-sign motion library in SignMotionDB.

Interface:
- get_motion(sign_id) -> Optional[CanonicalMotion]
- list_available_signs() -> List[str]
- validate_motion(motion) -> Dict[str, Any]
- save_motion(sign_id, motion) -> bool
- load_motion(sign_id) -> CanonicalMotion
"""

import threading
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from .canonical_motion import CanonicalMotion
from .motion_loader import MotionLoader
from .motion_validator import validate_motion as run_validation

logger = logging.getLogger("MotionDatabase")


class MotionDatabase:
    """
    Central database repository for Canonical SMPL-X motions.
    """

    def __init__(self, root_dir: Optional[Union[str, Path]] = None):
        base_dir = Path(__file__).resolve().parents[3]
        self.root_dir = Path(root_dir) if root_dir else (base_dir / "SignMotionDB")
        self.root_dir.mkdir(parents=True, exist_ok=True)

        self.loader = MotionLoader(db_dirs=[self.root_dir, base_dir / "SignAvatars" / "outputs" / "npy"])
        self._cache: Dict[str, CanonicalMotion] = {}
        self._lock = threading.Lock()

    def get_motion(self, sign_id: str) -> Optional[CanonicalMotion]:
        """
        Retrieves a motion by sign_id, utilizing memory caching.
        Returns None if the sign is not in the database.
        """
        clean_id = sign_id.strip().upper()

        with self._lock:
            if clean_id in self._cache:
                return self._cache[clean_id]

        motion = self.loader.load(clean_id)
        if motion is not None:
            # Validate on retrieval
            val_res = self.validate_motion(motion)
            if not val_res["valid"]:
                logger.warning(f"[MOTION DB] Retrieved motion '{clean_id}' has validation errors: {val_res['errors']}")

            with self._lock:
                self._cache[clean_id] = motion

        return motion

    def load_motion(self, sign_id: str) -> CanonicalMotion:
        """
        Loads a motion, raising KeyError if not found.
        """
        motion = self.get_motion(sign_id)
        if motion is None:
            raise KeyError(f"Motion '{sign_id}' not found in SignMotionDB")
        return motion

    def list_available_signs(self) -> List[str]:
        """Returns sorted list of available sign IDs."""
        return self.loader.list_available()

    def validate_motion(self, motion: Union[CanonicalMotion, Dict[str, Any]]) -> Dict[str, Any]:
        """Validates a CanonicalMotion against strict kinematic criteria."""
        return run_validation(motion)

    def save_motion(
        self,
        sign_id: str,
        motion: CanonicalMotion,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Permanently stores a validated CanonicalMotion in SignMotionDB/<SIGN_ID>/.
        """
        clean_id = sign_id.strip().upper()
        motion.sign_id = clean_id

        if metadata:
            motion.metadata.update(metadata)

        val_res = self.validate_motion(motion)
        if not val_res["valid"]:
            logger.error(f"[MOTION DB] Cannot save '{clean_id}': Validation failed with errors {val_res['errors']}")
            return False

        target_dir = self.root_dir / clean_id
        motion.save(target_dir)

        with self._lock:
            self._cache[clean_id] = motion

        logger.info(f"[MOTION DB] Successfully saved and cached sign '{clean_id}'")
        return True

    def clear_cache(self):
        """Clears in-memory motion cache."""
        with self._lock:
            self._cache.clear()


# Module-level singleton instance
_default_db: Optional[MotionDatabase] = None


def get_motion_database() -> MotionDatabase:
    """Returns singleton MotionDatabase instance."""
    global _default_db
    if _default_db is None:
        _default_db = MotionDatabase()
    return _default_db


# Convenient module-level functions
def get_motion(sign_id: str) -> Optional[CanonicalMotion]:
    return get_motion_database().get_motion(sign_id)


def list_available_signs() -> List[str]:
    return get_motion_database().list_available_signs()


def validate_motion(motion: Union[CanonicalMotion, Dict[str, Any]]) -> Dict[str, Any]:
    return get_motion_database().validate_motion(motion)


def save_motion(sign_id: str, motion: CanonicalMotion, metadata: Optional[Dict[str, Any]] = None) -> bool:
    return get_motion_database().save_motion(sign_id, motion, metadata=metadata)


def load_motion(sign_id: str) -> CanonicalMotion:
    return get_motion_database().load_motion(sign_id)
