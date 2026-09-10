import numpy as np
from pathlib import Path


TARGET_HEIGHT = 3.2
PELVIS_JOINT_INDEX = 0
LEFT_HAND_JOINT_INDEX = 20
RIGHT_HAND_JOINT_INDEX = 21
DIAGNOSTIC_FRAMES = (0, 30, 60, 90, 120, 150)


def _load_smplx_regressor() -> tuple[np.ndarray, np.ndarray]:
    model_path = (
        Path(__file__).resolve().parent
        / "common"
        / "utils"
        / "human_model_files"
        / "smplx"
        / "SMPLX_NEUTRAL.npz"
    )
    model = np.load(model_path, allow_pickle=False)
    return model["J_regressor"].astype(np.float32), model["v_template"].astype(np.float32)


def _print_root_and_hand_diagnostics(
    converted: np.ndarray,
    corrected: np.ndarray,
    regressor: np.ndarray,
    template: np.ndarray,
) -> None:
    pelvis_before = np.einsum("v,fvc->fc", regressor[PELVIS_JOINT_INDEX], converted)
    pelvis_after = np.einsum("v,fvc->fc", regressor[PELVIS_JOINT_INDEX], corrected)

    print("Before root correction pelvis min/max:", pelvis_before.min(axis=0), pelvis_before.max(axis=0))
    print("After root correction pelvis min/max:", pelvis_after.min(axis=0), pelvis_after.max(axis=0))
    before_xz = pelvis_before[:, (0, 2)] - pelvis_before[0, (0, 2)]
    after_xz = pelvis_after[:, (0, 2)] - pelvis_after[0, (0, 2)]
    print("Original pelvis displacement XZ max:", float(np.linalg.norm(before_xz, axis=1).max()))
    print("Corrected pelvis displacement XZ max:", float(np.linalg.norm(after_xz, axis=1).max()))
    print("Corrected pelvis Y displacement max:", float(np.abs(pelvis_after[:, 1] - pelvis_after[0, 1]).max()))

    joints = np.einsum("jv,fvc->fjc", regressor, converted)
    converted_template = template.copy()
    converted_template[:, 1] *= -1
    converted_template[:, 2] *= -1
    left_hand_vertices = np.argsort(
        np.linalg.norm(converted_template - joints[0, LEFT_HAND_JOINT_INDEX], axis=1)
    )[:128]
    right_hand_vertices = np.argsort(
        np.linalg.norm(converted_template - joints[0, RIGHT_HAND_JOINT_INDEX], axis=1)
    )[:128]
    for frame in DIAGNOSTIC_FRAMES:
        if frame >= len(corrected):
            continue
        left_delta = corrected[frame, left_hand_vertices] - corrected[0, left_hand_vertices]
        right_delta = corrected[frame, right_hand_vertices] - corrected[0, right_hand_vertices]
        print(
            f"Frame {frame} hand RMS displacement:",
            "left=",
            float(np.linalg.norm(left_delta, axis=1).mean()),
            "right=",
            float(np.linalg.norm(right_delta, axis=1).mean()),
        )


def convert_and_normalize_vertices(vertices: np.ndarray) -> np.ndarray:
    """Convert SMPL-X coordinates and normalize one complete motion sequence."""
    if vertices.ndim != 3 or vertices.shape[2] != 3:
        raise ValueError(f"Expected (frames, vertices, 3), got {vertices.shape}")

    source = np.asarray(vertices, dtype=np.float32)
    if not np.isfinite(source).all():
        raise ValueError("Motion contains NaN or infinite coordinates")

    # This SMPL-X export uses Y as the vertical axis with its headward
    # direction opposite to the Three.js scene's positive Y direction.
    converted = np.empty_like(source)
    converted[:, :, 0] = source[:, :, 0]
    converted[:, :, 1] = -source[:, :, 1]
    converted[:, :, 2] = -source[:, :, 2]

    regressor, template = _load_smplx_regressor()
    if regressor.shape != (55, vertices.shape[1]):
        raise ValueError(f"Unexpected SMPL-X J_regressor shape: {regressor.shape}")

    pelvis = np.einsum("v,fvc->fc", regressor[PELVIS_JOINT_INDEX], converted)
    root_delta = pelvis - pelvis[0]
    corrected = converted.copy()
    corrected[:, :, 0] -= root_delta[:, None, 0]
    corrected[:, :, 2] -= root_delta[:, None, 2]
    _print_root_and_hand_diagnostics(converted, corrected, regressor, template)

    global_min = corrected.min(axis=(0, 1))
    global_max = corrected.max(axis=(0, 1))
    global_extent = global_max - global_min
    height_extent = float(global_extent[1])
    if height_extent <= 0:
        raise ValueError("Motion has no positive vertical extent")

    center = (global_min + global_max) / 2.0
    scale = TARGET_HEIGHT / height_extent
    normalized = ((corrected - center) * scale).astype(np.float32, copy=False)

    print("Source axis min:", source.min(axis=(0, 1)))
    print("Source axis max:", source.max(axis=(0, 1)))
    print("Converted axis min:", global_min)
    print("Converted axis max:", global_max)
    print("Global center:", center)
    print("Global extent:", global_extent)
    print("Height extent:", height_extent)
    print("Normalization scale:", scale)
    print("Normalized axis min:", normalized.min(axis=(0, 1)))
    print("Normalized axis max:", normalized.max(axis=(0, 1)))

    return normalized