"""
SMPL-X Animation Sequencer Service.
Combines multiple real SMPL-X 3D vertex animations into one continuous motion sequence.
Handles temporal linear resampling to 30 FPS, smooth cosine transitions, and strict validation.
"""

import os
import uuid
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import httpx

from app.core.config import settings
from app.services.signavatar_client import signavatar_client, SignAvatarClient
from app.services.isl_animation_service import isl_animation_service, ISLAnimationService

logger = logging.getLogger("AnimationSequencer")

TARGET_FPS = 30
DEFAULT_TRANSITION_SEC = 0.20
VERTEX_COUNT = 10475
COORDINATE_DIM = 3


def resample_motion(vertices: np.ndarray, source_fps: float, target_fps: float = 30.0) -> np.ndarray:
    """
    Resample vertex animation temporally from source_fps to target_fps using linear interpolation.
    vertices shape: (N_orig, 10475, 3)
    returns shape: (N_target, 10475, 3)
    """
    if vertices.ndim != 3 or vertices.shape[1] != VERTEX_COUNT or vertices.shape[2] != COORDINATE_DIM:
        raise ValueError(f"Invalid vertex shape: {vertices.shape}. Expected (frames, {VERTEX_COUNT}, {COORDINATE_DIM})")

    n_orig = vertices.shape[0]
    if n_orig <= 1 or abs(float(source_fps) - float(target_fps)) < 1e-4:
        return np.ascontiguousarray(vertices, dtype=np.float32)

    # Duration = (N - 1) / FPS
    duration = (n_orig - 1) / float(source_fps)
    n_target = max(2, int(round(duration * float(target_fps))) + 1)

    # Linear interpolation across time indices [0, n_orig - 1]
    orig_indices = np.linspace(0.0, float(n_orig - 1), n_target, dtype=np.float32)
    idx_floor = np.floor(orig_indices).astype(np.int64)
    idx_ceil = np.minimum(idx_floor + 1, n_orig - 1)
    alpha = (orig_indices - idx_floor)[:, None, None]

    resampled = (1.0 - alpha) * vertices[idx_floor] + alpha * vertices[idx_ceil]
    return np.ascontiguousarray(resampled, dtype=np.float32)


def create_transition(pose_a: np.ndarray, pose_b: np.ndarray, num_frames: int = 6) -> np.ndarray:
    """
    Interpolate smoothly between final pose of sign A and initial pose of sign B.
    pose_a shape: (10475, 3)
    pose_b shape: (10475, 3)
    num_frames: number of intermediate frames (excluding pose_a and pose_b endpoints)
    returns shape: (num_frames, 10475, 3)
    """
    if num_frames <= 0:
        return np.empty((0, VERTEX_COUNT, COORDINATE_DIM), dtype=np.float32)

    # Cosine smooth easing strictly in range (0, 1) to avoid duplicated endpoint poses
    steps = np.arange(1, num_frames + 1, dtype=np.float32) / float(num_frames + 1)
    weights = 0.5 * (1.0 - np.cos(np.pi * steps))
    weights = weights[:, None, None]

    transition = (1.0 - weights) * pose_a[None, :, :] + weights * pose_b[None, :, :]
    return np.ascontiguousarray(transition, dtype=np.float32)


def sequence_animations(
    animations: List[np.ndarray],
    target_fps: float = 30.0,
    transition_sec: float = DEFAULT_TRANSITION_SEC
) -> np.ndarray:
    """
    Sequentially concatenates a list of SMPL-X vertex animations with blended transitions.
    """
    if not animations:
        return np.empty((0, VERTEX_COUNT, COORDINATE_DIM), dtype=np.float32)

    for i, anim in enumerate(animations):
        if anim.ndim != 3 or anim.shape[1] != VERTEX_COUNT or anim.shape[2] != COORDINATE_DIM:
            raise ValueError(f"Animation #{i} has invalid shape {anim.shape}")
        if not np.isfinite(anim).all():
            raise ValueError(f"Animation #{i} contains non-finite values (NaN/Inf)")

    if len(animations) == 1:
        return np.ascontiguousarray(animations[0], dtype=np.float32)

    num_trans_frames = max(1, int(round(transition_sec * target_fps)))
    chunks = []

    for i, anim in enumerate(animations):
        if i > 0:
            trans = create_transition(animations[i - 1][-1], anim[0], num_frames=num_trans_frames)
            chunks.append(trans)
        chunks.append(anim)

    combined = np.concatenate(chunks, axis=0)
    return np.ascontiguousarray(combined, dtype=np.float32)


class AnimationSequencer:
    """Service to load, resample, transition, and concatenate SMPL-X ISL animations."""

    def __init__(
        self,
        client: Optional[SignAvatarClient] = None,
        isl_service: Optional[ISLAnimationService] = None,
        target_fps: int = TARGET_FPS,
        transition_sec: float = DEFAULT_TRANSITION_SEC
    ):
        self.client = client or signavatar_client
        self.isl_service = isl_service or isl_animation_service
        self.target_fps = target_fps
        self.transition_sec = transition_sec

        # Directory for temporary/generated sequences
        self.base_dir = Path(__file__).resolve().parents[2]
        self.sequences_dir = self.base_dir / "outputs" / "sequences"
        self.sequences_dir.mkdir(parents=True, exist_ok=True)

        # Fallback local paths in workspace
        self.local_npy_dirs = [
            self.base_dir.parent / "SignAvatars" / "outputs" / "npy",
            self.base_dir / "animations",
            self.sequences_dir
        ]

    async def load_animation(self, gloss: str, meta: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, float]:
        """
        Loads the SMPL-X Float32 vertex array and FPS for a specific gloss.
        Tries local filesystem first for maximum speed; falls back to HTTP API streaming endpoint.
        """
        safe_name = self.client.normalize_gloss(gloss)
        source_fps = 50.0

        if meta and "fps" in meta and meta["fps"]:
            try:
                source_fps = float(meta["fps"])
            except (ValueError, TypeError):
                pass

        # 1. Check local NPY files
        for npy_dir in self.local_npy_dirs:
            local_npy = npy_dir / f"{safe_name}.npy"
            local_json = npy_dir / f"{safe_name}.json"
            if local_npy.is_file():
                if local_json.is_file():
                    try:
                        with open(local_json, "r", encoding="utf-8") as f:
                            jmeta = json.load(f)
                            if "fps" in jmeta:
                                source_fps = float(jmeta["fps"])
                    except Exception:
                        pass
                try:
                    data = np.load(local_npy, allow_pickle=False)
                    data = np.asarray(data, dtype=np.float32)
                    self._validate_raw_animation(data, safe_name)
                    return data, source_fps
                except Exception as e:
                    logger.warning("Failed loading local file %s: %s", local_npy, e)

        # 2. Fetch binary Float32 stream via HTTP client
        motion_url = f"{self.client.base_url}/motion/{safe_name}"
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            res = await http_client.get(motion_url)
            if res.status_code != 200:
                raise ValueError(f"Failed to fetch animation for gloss '{gloss}' from {motion_url}: HTTP {res.status_code}")

            if "X-FPS" in res.headers:
                try:
                    source_fps = float(res.headers["X-FPS"])
                except Exception:
                    pass

            binary_data = res.content
            expected_bytes_per_frame = VERTEX_COUNT * COORDINATE_DIM * 4
            if len(binary_data) % expected_bytes_per_frame != 0:
                raise ValueError(f"Invalid binary data size {len(binary_data)} for gloss '{gloss}'")

            frames = len(binary_data) // expected_bytes_per_frame
            data = np.frombuffer(binary_data, dtype=np.float32).reshape(frames, VERTEX_COUNT, COORDINATE_DIM)
            self._validate_raw_animation(data, safe_name)
            return np.ascontiguousarray(data, dtype=np.float32), source_fps

    def _validate_raw_animation(self, data: np.ndarray, gloss: str):
        if data.ndim != 3:
            raise ValueError(f"Gloss '{gloss}' animation has {data.ndim} dimensions; expected 3")
        if data.shape[1] != VERTEX_COUNT:
            raise ValueError(f"Gloss '{gloss}' vertex count is {data.shape[1]}; expected {VERTEX_COUNT}")
        if data.shape[2] != COORDINATE_DIM:
            raise ValueError(f"Gloss '{gloss}' coordinates are {data.shape[2]}; expected {COORDINATE_DIM}")
        if data.shape[0] < 1:
            raise ValueError(f"Gloss '{gloss}' animation has 0 frames")
        if not np.isfinite(data).all():
            raise ValueError(f"Gloss '{gloss}' animation contains non-finite numbers (NaN/Inf)")

    async def sequence_glosses(self, glosses: List[str]) -> Dict[str, Any]:
        """
        Full sequencing pipeline:
        1. Resolve all glosses using ISL animation service.
        2. If any gloss is unavailable, returns structured unavailable response without generating animation.
        3. If all available: loads, resamples to target_fps (30), creates transitions, concatenates, and saves sequence.
        """
        if not glosses:
            return {
                "available": False,
                "glosses": [],
                "reason": "Empty gloss sequence provided"
            }

        # Step 1: Resolve all glosses
        resolution = await self.isl_service.resolve_gloss_sequence(glosses)
        resolved_list = resolution.get("glosses", [])

        unavailable_items = [item for item in resolved_list if not item.get("available")]
        if unavailable_items:
            return {
                "available": False,
                "glosses": glosses,
                "unavailable": [
                    {
                        "gloss": item.get("gloss", ""),
                        "reason": item.get("reason", "No matching ISL animation available")
                    }
                    for item in unavailable_items
                ]
            }

        # Step 2: Load and resample all animations to TARGET_FPS
        resampled_animations = []
        for item in resolved_list:
            gloss_name = item.get("motion_key") or item["gloss"]
            raw_data, orig_fps = await self.load_animation(gloss_name, meta=item)
            resampled = resample_motion(raw_data, source_fps=orig_fps, target_fps=self.target_fps)
            resampled_animations.append(resampled)

        # Step 3: Concatenate with smooth transitions
        combined_vertices = sequence_animations(
            resampled_animations,
            target_fps=self.target_fps,
            transition_sec=self.transition_sec
        )

        total_frames = int(combined_vertices.shape[0])
        seq_uid = uuid.uuid4().hex[:8]
        clean_gloss_tag = "_".join(self.client.normalize_gloss(g) for g in glosses[:3])
        sequence_filename = f"sequence_{clean_gloss_tag}_{seq_uid}"

        npy_path = self.sequences_dir / f"{sequence_filename}.npy"
        json_path = self.sequences_dir / f"{sequence_filename}.json"

        # Step 4: Save combined animation and metadata
        np.save(str(npy_path), combined_vertices)

        animation_url = f"/api/signavatar/sequence/{sequence_filename}"
        metadata_url = f"/api/signavatar/sequence/{sequence_filename}/metadata"

        seq_metadata = {
            "available": True,
            "sequence_id": sequence_filename,
            "glosses": [item["gloss"] for item in resolved_list],
            "frames": total_frames,
            "fps": self.target_fps,
            "vertex_count": VERTEX_COUNT,
            "vertex_shape": [total_frames, VERTEX_COUNT, COORDINATE_DIM],
            "transition_sec": self.transition_sec,
            "transition_frames": max(1, int(round(self.transition_sec * self.target_fps))),
            "source": "BridgeConn Sign Dictionary ISL",
            "animation_url": animation_url,
            "metadata_url": metadata_url,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(seq_metadata, f, indent=2)

        return {
            "available": True,
            "sequence_id": sequence_filename,
            "glosses": [item["gloss"] for item in resolved_list],
            "fps": self.target_fps,
            "frames": total_frames,
            "vertex_count": VERTEX_COUNT,
            "animation_file": str(npy_path.relative_to(self.base_dir)).replace("\\", "/"),
            "animation_url": animation_url,
            "metadata_url": metadata_url,
            "source": "BridgeConn Sign Dictionary ISL",
            "vertices": combined_vertices
        }

    def sanitize_sequence_id(self, sequence_id: str) -> str:
        """Sanitizes sequence_id to prevent directory traversal and arbitrary filesystem injection."""
        if not sequence_id:
            raise ValueError("Sequence ID cannot be empty")

        clean = str(sequence_id).strip()
        if clean.endswith(".npy"):
            clean = clean[:-4]
        elif clean.endswith(".json"):
            clean = clean[:-5]

        # Reject directory traversal and invalid characters
        if ".." in clean or "/" in clean or "\\" in clean or ":" in clean or "~" in clean:
            raise ValueError("Invalid sequence ID: path traversal characters rejected")

        import re
        if not re.fullmatch(r"[a-zA-Z0-9_\-]+", clean):
            raise ValueError("Invalid sequence ID format")

        return clean

    def get_sequence_metadata(self, sequence_id: str) -> Dict[str, Any]:
        """Fetch saved JSON metadata for a sequence."""
        safe_id = self.sanitize_sequence_id(sequence_id)
        json_path = (self.sequences_dir / f"{safe_id}.json").resolve()

        if self.sequences_dir.resolve() not in json_path.parents and json_path.parent != self.sequences_dir.resolve():
            raise ValueError("Invalid sequence path")

        if not json_path.is_file():
            raise FileNotFoundError(f"Sequence metadata not found for ID: {sequence_id}")

        with open(json_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        meta.setdefault("available", True)
        meta.setdefault("animation_url", f"/api/signavatar/sequence/{safe_id}")
        meta.setdefault("metadata_url", f"/api/signavatar/sequence/{safe_id}/metadata")
        return meta

    def get_sequence_binary(self, sequence_id: str) -> Tuple[bytes, Dict[str, str]]:
        """
        Loads the combined SMPL-X Float32 vertex sequence and returns contiguous binary buffer
        along with validation headers.
        """
        safe_id = self.sanitize_sequence_id(sequence_id)
        npy_path = (self.sequences_dir / f"{safe_id}.npy").resolve()

        if self.sequences_dir.resolve() not in npy_path.parents and npy_path.parent != self.sequences_dir.resolve():
            raise ValueError("Invalid sequence path")

        if not npy_path.is_file():
            raise FileNotFoundError(f"Sequence animation not found for ID: {sequence_id}")

        data = np.load(npy_path, allow_pickle=False)
        data = np.asarray(data, dtype=np.float32)

        self._validate_raw_animation(data, safe_id)

        frames = int(data.shape[0])
        vertices = int(data.shape[1])
        components = int(data.shape[2])

        # Read optional metadata for FPS & source
        fps_val = self.target_fps
        source_val = "BridgeConn Sign Dictionary ISL"
        try:
            meta = self.get_sequence_metadata(safe_id)
            if "fps" in meta:
                fps_val = meta["fps"]
            if "source" in meta:
                source_val = meta["source"]
        except Exception:
            pass

        binary_data = np.ascontiguousarray(data, dtype=np.float32).tobytes()
        expected_bytes = frames * vertices * components * 4
        actual_bytes = len(binary_data)

        if actual_bytes != expected_bytes:
            raise ValueError(f"Binary sequence size mismatch: expected {expected_bytes} bytes, got {actual_bytes}")

        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Length": str(actual_bytes),
            "X-Frames": str(frames),
            "X-FPS": str(fps_val),
            "X-Vertices": str(vertices),
            "X-Components": str(components),
            "X-Dtype": "float32",
            "X-Source": str(source_val)
        }

        return binary_data, headers


animation_sequencer = AnimationSequencer()

