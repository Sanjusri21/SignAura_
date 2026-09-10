import os
import numpy as np

from motion_transform import convert_and_normalize_vertices

MOTION_DIR = r".\outputs\npy"
OUTPUT_DIR = r".\outputs\npy"

# Verified motion sequence
motion_sequence = [
    ("welcome", "9310"),
    ("help", "13847"),
    ("you", "8597"),
]

motions = []

print("=" * 60)
print("COMBINING SIGNAVATAR MOTIONS")
print("=" * 60)

for word, motion_id in motion_sequence:

    path = os.path.join(
        MOTION_DIR,
        f"{motion_id}.npy"
    )

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Motion file not found: {path}"
        )

    motion = np.load(path)

    print(
        f"{word:10} → {motion_id:6} "
        f"→ {motion.shape}"
    )

    motions.append(motion)

# Combine frames
combined = np.concatenate(
    motions,
    axis=0
)

combined = convert_and_normalize_vertices(combined)

output_path = os.path.join(
    OUTPUT_DIR,
    "welcome_help_you.npy"
)

np.save(
    output_path,
    combined
)

print()
print("=" * 60)
print("COMBINATION COMPLETE")
print("=" * 60)

print("Total frames :", len(combined))
print("Shape        :", combined.shape)
print("Saved        :", output_path)
print("=" * 60)