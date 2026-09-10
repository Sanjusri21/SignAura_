import sys
import os
import numpy as np
import trimesh
import pyrender
import imageio.v2 as imageio
import smplx


# ============================================================
# CONFIG
# ============================================================

MODEL_PATH = r".\common\utils\human_model_files"
OUTPUT_GIF_DIR = r".\outputs\gifs"
OUTPUT_NPY_DIR = r".\outputs\npy"

VIEWPORT_WIDTH = 640
VIEWPORT_HEIGHT = 640
FPS = 20


# ============================================================
# GET MOTION ID
# ============================================================

if len(sys.argv) < 2:
    print("Usage:")
    print("  python render_motion.py 10010")
    print()
    print("Example:")
    print("  python render_motion.py 10014")
    sys.exit(1)

motion_id = sys.argv[1]

vertices_file = f"signavatar_{motion_id}_vertices.npy"

if not os.path.exists(vertices_file):
    print(f"ERROR: Vertices file not found:")
    print(vertices_file)
    print()
    print("Generate the vertices file first.")
    sys.exit(1)


# ============================================================
# CREATE OUTPUT DIRECTORIES
# ============================================================

os.makedirs(OUTPUT_GIF_DIR, exist_ok=True)
os.makedirs(OUTPUT_NPY_DIR, exist_ok=True)


# ============================================================
# LOAD VERTICES
# ============================================================

vertices = np.load(vertices_file)

print()
print("=" * 50)
print(f"Motion ID: {motion_id}")
print("Loaded vertices:", vertices.shape)
print("=" * 50)


# ============================================================
# LOAD SMPL-X MODEL
# ============================================================

print("Loading SMPL-X model...")

model = smplx.create(
    MODEL_PATH,
    model_type="smplx",
    gender="neutral",
    use_pca=False,
    batch_size=1,
)

faces = model.faces

print("Faces:", faces.shape)


# ============================================================
# CREATE RENDERER
# ============================================================

renderer = pyrender.OffscreenRenderer(
    viewport_width=VIEWPORT_WIDTH,
    viewport_height=VIEWPORT_HEIGHT
)


# ============================================================
# CAMERA
# ============================================================

camera = pyrender.PerspectiveCamera(
    yfov=np.pi / 3.0
)

camera_pose = np.eye(4)
camera_pose[2, 3] = 3.0


# ============================================================
# LIGHT
# ============================================================

light = pyrender.DirectionalLight(
    color=np.ones(3),
    intensity=3.0
)


# ============================================================
# RENDER FRAMES
# ============================================================

frames = []

print()
print("Rendering...")

total_frames = len(vertices)

for i, frame_vertices in enumerate(vertices):

    mesh = trimesh.Trimesh(
        vertices=frame_vertices,
        faces=faces,
        process=False
    )

    render_mesh = pyrender.Mesh.from_trimesh(
        mesh,
        smooth=False
    )

    scene = pyrender.Scene()

    scene.add(render_mesh)

    scene.add(
        camera,
        pose=camera_pose
    )

    scene.add(
        light,
        pose=camera_pose
    )

    color, depth = renderer.render(scene)

    frames.append(color)

    if i % 10 == 0 or i == total_frames - 1:
        print(
            f"Rendered frame {i + 1}/{total_frames}"
        )


# ============================================================
# CLEANUP
# ============================================================

renderer.delete()


# ============================================================
# SAVE GIF
# ============================================================

output_gif = os.path.join(
    OUTPUT_GIF_DIR,
    f"{motion_id}.gif"
)

imageio.mimsave(
    output_gif,
    frames,
    fps=FPS
)


# ============================================================
# COPY/STORE NPY IN OUTPUT DIRECTORY
# ============================================================

output_npy = os.path.join(
    OUTPUT_NPY_DIR,
    f"{motion_id}.npy"
)

np.save(output_npy, vertices)


# ============================================================
# DONE
# ============================================================

print()
print("=" * 50)
print("Rendering complete!")
print("=" * 50)
print("Motion ID :", motion_id)
print("Frames    :", total_frames)
print("Vertices  :", vertices.shape)
print("GIF       :", output_gif)
print("NPY       :", output_npy)
print("=" * 50)