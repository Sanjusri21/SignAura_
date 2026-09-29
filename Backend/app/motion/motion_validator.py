"""
SMPL-X Motion Validation Module.

Validates CanonicalMotion or raw parameter dictionaries against strict kinematic,
geometric, and temporal criteria.

Validation Criteria:
1. Array shapes matching canonical SMPL-X parameter specifications
2. Frame count consistency across all kinematic components
3. Absence of NaN / Infinite floating point values
4. Parameter value ranges (rotvec norms within valid Euler/Rodrigues bounds, valid translation bounds)
5. Body and hand pose availability (whether hand/body joints are articulated or stationary)
6. FPS consistency (positive, non-zero, within standard ranges 10-120)
7. Coordinate and temporal continuity (absence of unphysical inter-frame velocity explosions)
"""

import logging
from typing import Dict, Any, List, Union

import numpy as np

logger = logging.getLogger("MotionValidator")

# Expected SMPL-X parameter dimensions per frame
EXPECTED_DIMS = {
    "global_orient": 3,
    "body_pose": 63,
    "left_hand_pose": 45,
    "right_hand_pose": 45,
    "jaw_pose": 3,
    "transl": 3,
}

MAX_ROTVEC_NORM = 2.0 * np.pi + 1.0  # Safe Rodrigues angle threshold
MAX_DISCONTINUITY_THRESHOLD = 3.5    # Max radians/frame jump for joints before flagging discontinuity


def validate_motion(motion: Any) -> Dict[str, Any]:
    """
    Validates a CanonicalMotion instance or dict containing SMPL-X parameters.

    Returns:
        {
            "valid": bool,
            "errors": List[str],
            "warnings": List[str],
            "details": Dict[str, Any]
        }
    """
    errors: List[str] = []
    warnings: List[str] = []
    details: Dict[str, Any] = {}

    # 1. Type / Property Extraction
    sign_id = getattr(motion, "sign_id", None) or (motion.get("sign_id") if isinstance(motion, dict) else "UNKNOWN")
    fps = getattr(motion, "fps", None) or (motion.get("fps") if isinstance(motion, dict) else None)
    num_frames = getattr(motion, "num_frames", None) or (motion.get("num_frames") if isinstance(motion, dict) else None)

    # 2. FPS Check
    if fps is None:
        errors.append("FPS is missing or None")
    else:
        try:
            fps_val = float(fps)
            if fps_val <= 0:
                errors.append(f"FPS must be positive, got {fps_val}")
            elif fps_val < 10.0 or fps_val > 120.0:
                warnings.append(f"Unusual FPS: {fps_val} (expected 10 - 120)")
            details["fps"] = fps_val
        except (ValueError, TypeError):
            errors.append(f"Invalid FPS type: {type(fps)}")

    # 3. Frame count check
    if num_frames is None:
        errors.append("num_frames is missing or None")
    else:
        try:
            n_frames = int(num_frames)
            if n_frames <= 0:
                errors.append(f"num_frames must be > 0, got {n_frames}")
            details["num_frames"] = n_frames
        except (ValueError, TypeError):
            errors.append(f"Invalid num_frames type: {type(num_frames)}")
            n_frames = 0

    # 4. Check each kinematic array
    arrays_to_check = [
        "global_orient",
        "body_pose",
        "left_hand_pose",
        "right_hand_pose",
        "jaw_pose",
        "transl",
    ]

    for name in arrays_to_check:
        arr = getattr(motion, name, None) if not isinstance(motion, dict) else motion.get(name)
        if arr is None:
            errors.append(f"Missing required parameter array: '{name}'")
            continue

        if not isinstance(arr, np.ndarray):
            try:
                arr = np.asarray(arr, dtype=np.float32)
            except Exception as e:
                errors.append(f"Parameter '{name}' cannot be converted to numpy array: {e}")
                continue

        # Check dimension (must be 2D: (T, D))
        if arr.ndim != 2:
            errors.append(f"Array '{name}' has invalid dimension {arr.ndim}, expected 2 (frames, dim)")
            continue

        frames, dim = arr.shape
        expected_dim = EXPECTED_DIMS[name]
        if dim != expected_dim:
            errors.append(f"Array '{name}' has {dim} columns, expected {expected_dim}")

        if n_frames > 0 and frames != n_frames:
            errors.append(f"Frame count mismatch for '{name}': {frames} vs num_frames {n_frames}")

        # Check NaN and Inf
        if not np.isfinite(arr).all():
            nan_count = int(np.isnan(arr).sum())
            inf_count = int(np.isinf(arr).sum())
            errors.append(f"Array '{name}' contains non-finite values (NaN: {nan_count}, Inf: {inf_count})")

        # Range verification for rotations (Rodrigues vector angle norm)
        if "pose" in name or "orient" in name:
            reshaped_rot = arr.reshape(-1, 3)
            rot_norms = np.linalg.norm(reshaped_rot, axis=-1)
            max_rot = float(np.max(rot_norms)) if len(rot_norms) > 0 else 0.0
            if max_rot > MAX_ROTVEC_NORM:
                warnings.append(f"Large rotation angle in '{name}': max magnitude {max_rot:.2f} rad")

        # Translation range check
        if name == "transl":
            trans_max = float(np.max(np.abs(arr))) if len(arr) > 0 else 0.0
            if trans_max > 10.0:
                warnings.append(f"Extreme translation values: max absolute {trans_max:.2f} meters")

        # 5. Temporal discontinuity check (velocity spikes)
        if frames > 1 and np.isfinite(arr).all():
            diffs = np.diff(arr, axis=0)
            max_delta = float(np.max(np.abs(diffs)))
            if "pose" in name and max_delta > MAX_DISCONTINUITY_THRESHOLD:
                warnings.append(f"Potential temporal discontinuity in '{name}': max inter-frame step {max_delta:.2f} rad")

    # 6. Hand availability flags
    lh = getattr(motion, "left_hand_pose", None) if not isinstance(motion, dict) else motion.get("left_hand_pose")
    rh = getattr(motion, "right_hand_pose", None) if not isinstance(motion, dict) else motion.get("right_hand_pose")

    lh_active = False
    rh_active = False
    if lh is not None and isinstance(lh, np.ndarray) and lh.size > 0:
        lh_active = float(np.std(lh)) > 1e-4
    if rh is not None and isinstance(rh, np.ndarray) and rh.size > 0:
        rh_active = float(np.std(rh)) > 1e-4

    details["left_hand_active"] = lh_active
    details["right_hand_active"] = rh_active

    # Check if both hands are completely inactive
    if not lh_active and not rh_active:
        warnings.append("Both hands are stationary (zero articulation detected)")

    is_valid = len(errors) == 0

    if is_valid:
        logger.info(f"[VALIDATION] Motion '{sign_id}' valid ({n_frames} frames, {fps} fps)")
    else:
        logger.error(f"[VALIDATION] Motion '{sign_id}' validation FAILED: {errors}")

    return {
        "valid": is_valid,
        "sign_id": sign_id,
        "errors": errors,
        "warnings": warnings,
        "details": details,
    }
