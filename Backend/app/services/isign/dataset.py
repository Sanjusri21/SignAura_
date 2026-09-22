"""
Resource inspector and filesystem access for iSign Benchmark Dataset.
Inspects local presence of pose and video files without loading full datasets into memory.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from .config import (
    ISIGN_DATA_DIR,
    ISIGN_POSES_DIR,
    ISIGN_VIDEOS_DIR,
    ISIGN_METADATA_PATH,
    ISIGN_WORD_PRESENCE_PATH,
    ISIGN_WORD_DESCRIPTION_PATH,
    POSE_PART_FILES,
    VIDEO_PART_FILES,
)


class ISignDatasetInspector:
    """Manages filesystem checks for iSign resources."""

    def __init__(
        self,
        poses_dir: Optional[Path] = None,
        videos_dir: Optional[Path] = None,
        data_dir: Optional[Path] = None,
    ):
        self.data_dir = data_dir or ISIGN_DATA_DIR
        self.poses_dir = poses_dir or ISIGN_POSES_DIR
        self.videos_dir = videos_dir or ISIGN_VIDEOS_DIR

    def is_pose_available(self, uid: str) -> bool:
        """Checks if a keypoint file (.pose or .npz) exists for the given UID."""
        if not self.poses_dir.exists():
            return False
        clean_uid = uid.strip()
        candidates = [
            self.poses_dir / f"{clean_uid}.npz",
            self.poses_dir / f"{clean_uid}.pose",
            self.poses_dir / f"{clean_uid}.npy",
        ]
        return any(p.exists() and p.is_file() for p in candidates)

    def is_video_available(self, uid: str) -> bool:
        """Checks if an MP4 video clip exists for the given UID."""
        if not self.videos_dir.exists():
            return False
        clean_uid = uid.strip()
        video_path = self.videos_dir / f"{clean_uid}.mp4"
        return video_path.exists() and video_path.is_file()

    def get_pose_file(self, uid: str) -> Optional[Path]:
        """Returns the path to the pose file if it exists."""
        clean_uid = uid.strip()
        for ext in (".npz", ".pose", ".npy"):
            p = self.poses_dir / f"{clean_uid}{ext}"
            if p.exists() and p.is_file():
                return p
        return None

    def get_video_file(self, uid: str) -> Optional[Path]:
        """Returns the path to the video file if it exists."""
        p = self.videos_dir / f"{uid.strip()}.mp4"
        if p.exists() and p.is_file():
            return p
        return None

    def get_dataset_overview(self) -> Dict[str, Any]:
        """Returns diagnostic info about which iSign components are present on disk."""
        data_dir_exists = self.data_dir.exists()
        metadata_exists = ISIGN_METADATA_PATH.exists()
        wp_exists = ISIGN_WORD_PRESENCE_PATH.exists()
        wd_exists = ISIGN_WORD_DESCRIPTION_PATH.exists()

        pose_parts_present = [
            f for f in POSE_PART_FILES if (self.data_dir / f).exists()
        ]
        video_parts_present = [
            f for f in VIDEO_PART_FILES if (self.data_dir / f).exists()
        ]

        extracted_poses_count = 0
        if self.poses_dir.exists():
            extracted_poses_count = len(list(self.poses_dir.glob("*.npz"))) + len(list(self.poses_dir.glob("*.pose")))

        extracted_videos_count = 0
        if self.videos_dir.exists():
            extracted_videos_count = len(list(self.videos_dir.glob("*.mp4")))

        return {
            "data_dir": str(self.data_dir),
            "data_dir_exists": data_dir_exists,
            "metadata_csv": {
                "path": str(ISIGN_METADATA_PATH),
                "exists": metadata_exists,
                "size_bytes": ISIGN_METADATA_PATH.stat().st_size if metadata_exists else 0,
            },
            "word_presence_csv": {
                "path": str(ISIGN_WORD_PRESENCE_PATH),
                "exists": wp_exists,
            },
            "word_description_csv": {
                "path": str(ISIGN_WORD_DESCRIPTION_PATH),
                "exists": wd_exists,
            },
            "pose_archives": {
                "expected": POSE_PART_FILES,
                "present": pose_parts_present,
                "extracted_poses_count": extracted_poses_count,
            },
            "video_archives": {
                "expected": VIDEO_PART_FILES,
                "present": video_parts_present,
                "extracted_videos_count": extracted_videos_count,
            },
            "license": "CC BY-NC-SA 4.0 (Non-Commercial Research Use Only)",
            "benchmark_source": "Exploration-Lab/iSign (ACL 2024)",
        }


isign_inspector = ISignDatasetInspector()
