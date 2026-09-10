import pickle
import torch
import smplx
import numpy as np
import os
import sys


# ============================================================
# CONFIG
# ============================================================

MODEL_PATH = r".\common\utils\human_model_files"
MOTION_DIR = r"C:\Users\sanju\Downloads\hamnosys_pkls_default_shape\hamnosys_pkls_default_shape"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# ============================================================
# GET MOTION ID
# ============================================================

if len(sys.argv) < 2:
    print()
    print("Usage:")
    print("  python test_motion.py <motion_id>")
    print()
    print("Examples:")
    print("  python test_motion.py 9310")
    print("  python test_motion.py 3354")
    print()
    sys.exit(1)

motion_id = sys.argv[1]

PKL_PATH = os.path.join(
    MOTION_DIR,
    motion_id + ".pkl"
)

OUTPUT_FILE = f"signavatar_{motion_id}_vertices.npy"


# ============================================================
# CHECK FILE
# ============================================================

if not os.path.exists(PKL_PATH):
    print()
    print("ERROR: Motion PKL not found:")
    print(PKL_PATH)
    print()
    sys.exit(1)


# ============================================================
# DEVICE
# ============================================================

print()
print("=" * 60)
print("Generating SignAvatar vertices")
print("=" * 60)

print("Motion ID :", motion_id)
print("PKL       :", PKL_PATH)
print("Device    :", DEVICE)


# ============================================================
# LOAD MOTION
# ============================================================

print()
print("Loading motion data...")

with open(PKL_PATH, "rb") as f:
    data = pickle.load(f)

motion = data["smplx"]

print("Motion shape:", motion.shape)


# ============================================================
# CONVERT TO TENSOR
# ============================================================

motion = torch.tensor(
    motion,
    dtype=torch.float32,
    device=DEVICE
)

num_frames = motion.shape[0]

print("Frames:", num_frames)


# ============================================================
# LOAD SMPL-X
# ============================================================

print()
print("Loading SMPL-X model...")

model = smplx.create(
    MODEL_PATH,
    model_type="smplx",
    gender="neutral",
    use_pca=False,
    batch_size=num_frames,
).to(DEVICE)

print("SMPL-X loaded successfully")


# ============================================================
# GENERATE VERTICES
# ============================================================

print()
print("Generating vertices...")

with torch.no_grad():

    output = model(
        global_orient=motion[:, 0:3],
        body_pose=motion[:, 3:66],
        left_hand_pose=motion[:, 66:111],
        right_hand_pose=motion[:, 111:156],
        jaw_pose=motion[:, 156:159],
        betas=motion[:, 159:169],
        expression=motion[:, 169:179],
        transl=motion[:, 179:182],
    )

vertices = output.vertices


# ============================================================
# SAVE
# ============================================================

print()
print("Generation successful!")

print("Vertices shape:", vertices.shape)
print("Device:", vertices.device)

vertices_cpu = vertices.cpu().numpy()

np.save(
    OUTPUT_FILE,
    vertices_cpu
)

print()
print("=" * 60)
print("SAVED")
print("=" * 60)
print(OUTPUT_FILE)
print("Shape:", vertices_cpu.shape)
print("=" * 60)