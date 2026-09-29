"""
SMPL-X Motion Loader.

Responsible for locating, reading, and loading CanonicalMotion files from
SignMotionDB and fallback directories.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from .canonical_motion import CanonicalMotion

logger = logging.getLogger("MotionLoader")


class MotionLoader:
    """
    Finds and deserializes CanonicalMotion records from disk.
    """

    def __init__(self, db_dirs: Optional[List[Path]] = None):
        self.db_dirs: List[Path] = []
        if db_dirs:
            self.db_dirs.extend([Path(d) for d in db_dirs])
        else:
            # Standard search locations
            base_dir = Path(__file__).resolve().parents[3]
            self.db_dirs.append(base_dir / "SignMotionDB")
            self.db_dirs.append(base_dir / "Backend" / "SignMotionDB")
            self.db_dirs.append(base_dir / "SignAvatars" / "outputs" / "npy")

    def find_motion_dir(self, sign_id: str) -> Optional[Path]:
        """
        Locates the directory containing motion.npz for the given sign_id.
        Checks exact case and normalized uppercase/lowercase.
        """
        clean = sign_id.strip()
        variants = [clean, clean.upper(), clean.lower()]

        # Common aliases (e.g. HELP -> help_2)
        if clean.upper() == "HELP":
            variants.extend(["HELP_2", "help_2"])
        elif clean.upper() == "TEACHER":
            variants.extend(["TEACHER_2", "teacher_2"])

        for db_dir in self.db_dirs:
            if not db_dir.is_dir():
                continue

            for v in variants:
                # 1. SignMotionDB standard: db_dir / <SIGN> / motion.npz
                motion_file = db_dir / v / "motion.npz"
                if motion_file.is_file():
                    return db_dir / v

                # 2. Legacy flat format: db_dir / <SIGN>_smplx_params.npz
                legacy_npz = db_dir / f"{v.lower()}_smplx_params.npz"
                if legacy_npz.is_file():
                    return legacy_npz

                # 3. Direct npz: db_dir / <SIGN>.npz
                direct_npz = db_dir / f"{v}.npz"
                if direct_npz.is_file():
                    return direct_npz

        return None

    def load(self, sign_id: str) -> Optional[CanonicalMotion]:
        """
        Loads CanonicalMotion for a sign_id. Returns None if not found.
        """
        clean_id = sign_id.strip().upper()
        location = self.find_motion_dir(clean_id)

        if not location:
            logger.warning(f"[MOTION DB] Sign '{clean_id}' not found in search paths")
            return None

        try:
            if location.is_dir():
                npz_file = location / "motion.npz"
                json_file = location / "metadata.json"
                motion = CanonicalMotion.from_npz(
                    npz_file,
                    metadata_path=json_file if json_file.is_file() else None,
                    fallback_sign_id=clean_id
                )
            else:
                # Flat legacy NPZ file
                json_candidate = location.parent / f"{location.stem.replace('_smplx_params', '')}.json"
                motion = CanonicalMotion.from_npz(
                    location,
                    metadata_path=json_candidate if json_candidate.is_file() else None,
                    fallback_sign_id=clean_id
                )

            logger.info(f"[MOTION DB] Loaded {clean_id} ({motion.num_frames} frames, {motion.fps} fps)")
            return motion
        except Exception as e:
            logger.error(f"[MOTION DB] Error loading motion '{clean_id}' from {location}: {e}")
            return None

    def list_available(self) -> List[str]:
        """Discovers all available sign IDs across configured databases."""
        available = set()

        for db_dir in self.db_dirs:
            if not db_dir.is_dir():
                continue

            # Standard structured dirs: <SIGN>/motion.npz
            for entry in db_dir.iterdir():
                if entry.is_dir() and (entry / "motion.npz").is_file():
                    available.add(entry.name.upper())

            # Legacy flat files: *_smplx_params.npz
            for npz in db_dir.glob("*_smplx_params.npz"):
                stem = npz.stem.replace("_smplx_params", "")
                available.add(stem.upper())

        return sorted(list(available))
