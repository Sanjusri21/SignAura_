import os
import sys
import numpy as np
import trimesh
import pyrender
import imageio.v2 as imageio
import smplx


# ============================================================
# CONFIG
# ============================================================

MODEL_PATH = r".\common\utils\human_model_files"

WIDTH = 640
HEIGHT = 640
FPS = 20

# Avatar visual settings
AVATAR_COLOR = [0.25, 0.55, 0.90, 1.0]

# Camera padding
CAMERA_PADDING = 1.20


# ============================================================
# ARGUMENT CHECK
# ============================================================

if len(sys.argv) < 3:

    print()
    print("Usage:")
    print("python render_combined.py input.npy output.gif")
    print()

    sys.exit(1)


INPUT_FILE = sys.argv[1]
OUTPUT_FILE = sys.argv[2]


# ============================================================
# HEADER
# ============================================================

print("=" * 60)
print("RENDERING COMBINED SIGNAVATAR")
print("=" * 60)


# ============================================================
# LOAD VERTICES
# ============================================================

vertices = np.load(INPUT_FILE)

print("Input :", INPUT_FILE)
print("Shape :", vertices.shape)


if vertices.ndim != 3 or vertices.shape[2] != 3:

    print()
    print("ERROR: Expected:")
    print("(frames, vertices, 3)")
    print()

    sys.exit(1)


# ============================================================
# CHECK DATA
# ============================================================

print()
print("Checking vertex data...")

print("Min :", np.min(vertices))
print("Max :", np.max(vertices))
print("NaN :", np.isnan(vertices).any())
print("Inf :", np.isinf(vertices).any())


if np.isnan(vertices).any():

    print("ERROR: Vertices contain NaN.")
    sys.exit(1)


if np.isinf(vertices).any():

    print("ERROR: Vertices contain Inf.")
    sys.exit(1)


# ============================================================
# ANALYZE SOURCE COORDINATES
# ============================================================

print()
print("=" * 60)
print("ANALYZING SIGNAVATAR COORDINATES")
print("=" * 60)

source_x = vertices[:, :, 0]
source_y = vertices[:, :, 1]
source_z = vertices[:, :, 2]

print(
    "Original X min/max:",
    np.min(source_x),
    np.max(source_x)
)

print(
    "Original Y min/max:",
    np.min(source_y),
    np.max(source_y)
)

print(
    "Original Z min/max:",
    np.min(source_z),
    np.max(source_z)
)


# ============================================================
# GLOBAL BOUNDS
# ============================================================

global_min = np.min(vertices, axis=(0, 1))
global_max = np.max(vertices, axis=(0, 1))

center = (global_min + global_max) / 2.0
extent = global_max - global_min

print()
print("=" * 60)
print("GLOBAL BOUNDS")
print("=" * 60)

print("Min    :", global_min)
print("Max    :", global_max)
print("Center :", center)
print("Extent :", extent)


max_extent = float(np.max(extent))

if max_extent <= 0:

    print("ERROR: Invalid vertex extent.")
    sys.exit(1)


# ============================================================
# NORMALIZATION
# ============================================================

scale = 1.0

print()
print("=" * 60)
print("NORMALIZING")
print("=" * 60)

print("Scale:", scale)


normalized_vertices = vertices


print(
    "Normalized min:",
    np.min(normalized_vertices, axis=(0, 1))
)

print(
    "Normalized max:",
    np.max(normalized_vertices, axis=(0, 1))
)


# ============================================================
# FINAL NORMALIZED BOUNDS
# ============================================================

final_min = np.min(
    normalized_vertices,
    axis=(0, 1)
)

final_max = np.max(
    normalized_vertices,
    axis=(0, 1)
)

final_center = (
    final_min + final_max
) / 2.0

final_extent = (
    final_max - final_min
)


print()
print("=" * 60)
print("FINAL CAMERA BOUNDS")
print("=" * 60)

print("Final min    :", final_min)
print("Final max    :", final_max)
print("Final center :", final_center)
print("Final extent :", final_extent)


# ============================================================
# LOAD SMPL-X
# ============================================================

print()
print("=" * 60)
print("LOADING SMPL-X MODEL")
print("=" * 60)

model = smplx.create(
    MODEL_PATH,
    model_type="smplx",
    gender="neutral",
    use_pca=False,
    batch_size=1
)

faces = model.faces

print("Faces:", faces.shape)


# ============================================================
# MATERIAL
# ============================================================

material = pyrender.MetallicRoughnessMaterial(
    baseColorFactor=AVATAR_COLOR,
    metallicFactor=0.0,
    roughnessFactor=0.65
)


# ============================================================
# ORTHOGRAPHIC CAMERA
# ============================================================

print()
print("=" * 60)
print("CREATING ORTHOGRAPHIC CAMERA")
print("=" * 60)


# The avatar height is around 3.2 after normalization.
# Use a little extra space around it.

camera_height = (
    max(
        final_extent[1],
        final_extent[0],
        final_extent[2]
    )
    * CAMERA_PADDING
)

# Make sure camera is never too small.
camera_height = max(camera_height, 3.8)

camera = pyrender.OrthographicCamera(
    xmag=camera_height / 2.0,
    ymag=camera_height / 2.0
)


# ============================================================
# CAMERA POSITION
# ============================================================

camera_pose = np.eye(4)

# Camera looks toward negative Z.
#
# Put camera in front of avatar.

camera_pose[0, 3] = 0.0
camera_pose[1, 3] = 0.0
camera_pose[2, 3] = 4.0


print("Camera X:", camera_pose[0, 3])
print("Camera Y:", camera_pose[1, 3])
print("Camera Z:", camera_pose[2, 3])

print("Camera size:", camera_height)


# ============================================================
# LIGHTING
# ============================================================

print()
print("Creating lights...")


main_light = pyrender.DirectionalLight(
    color=np.ones(3),
    intensity=4.0
)


fill_light = pyrender.DirectionalLight(
    color=np.ones(3),
    intensity=2.0
)


# ============================================================
# RENDERER
# ============================================================

print()
print("Creating renderer...")


renderer = pyrender.OffscreenRenderer(
    viewport_width=WIDTH,
    viewport_height=HEIGHT,
    point_size=1.0
)


# ============================================================
# OUTPUT DIRECTORIES
# ============================================================

output_directory = os.path.dirname(
    os.path.abspath(OUTPUT_FILE)
)

os.makedirs(
    output_directory,
    exist_ok=True
)


preview_directory = os.path.join(
    output_directory,
    "previews"
)

os.makedirs(
    preview_directory,
    exist_ok=True
)


# ============================================================
# RENDER
# ============================================================

print()
print("=" * 60)
print("RENDERING")
print("=" * 60)

total_frames = len(normalized_vertices)

print("Total frames:", total_frames)

frames = []


for i, frame_vertices in enumerate(
    normalized_vertices
):

    # --------------------------------------------------------
    # CREATE TRIMESH
    # --------------------------------------------------------

    mesh = trimesh.Trimesh(
        vertices=frame_vertices,
        faces=faces,
        process=False
    )


    # --------------------------------------------------------
    # FIX NORMALS
    # --------------------------------------------------------

    try:

        mesh.remove_unreferenced_vertices()
        mesh.fix_normals()

    except Exception:

        pass


    # --------------------------------------------------------
    # PYRENDER MESH
    # --------------------------------------------------------

    render_mesh = pyrender.Mesh.from_trimesh(
        mesh,
        material=material,
        smooth=False
    )


    # --------------------------------------------------------
    # CREATE SCENE
    # --------------------------------------------------------

    scene = pyrender.Scene(
        bg_color=np.array(
            [1.0, 1.0, 1.0, 1.0]
        ),
        ambient_light=np.array(
            [0.35, 0.35, 0.35]
        )
    )


    # --------------------------------------------------------
    # ADD AVATAR
    # --------------------------------------------------------

    scene.add(
        render_mesh
    )


    # --------------------------------------------------------
    # ADD CAMERA
    # --------------------------------------------------------

    scene.add(
        camera,
        pose=camera_pose
    )


    # --------------------------------------------------------
    # MAIN LIGHT
    # --------------------------------------------------------

    light_pose = np.eye(4)

    light_pose[0, 3] = 2.0
    light_pose[1, 3] = 3.0
    light_pose[2, 3] = 4.0

    scene.add(
        main_light,
        pose=light_pose
    )


    # --------------------------------------------------------
    # FILL LIGHT
    # --------------------------------------------------------

    fill_pose = np.eye(4)

    fill_pose[0, 3] = -2.0
    fill_pose[1, 3] = 1.0
    fill_pose[2, 3] = 3.0

    scene.add(
        fill_light,
        pose=fill_pose
    )


    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    try:

        color, depth = renderer.render(
            scene,
            flags=pyrender.RenderFlags.RGBA
        )

    except Exception as e:

        print()
        print("ERROR rendering frame:", i)
        print(e)

        renderer.delete()

        sys.exit(1)


    # --------------------------------------------------------
    # RGBA -> RGB
    # --------------------------------------------------------

    if color.shape[2] == 4:

        color = color[:, :, :3]


    # --------------------------------------------------------
    # CHECK FRAME
    # --------------------------------------------------------

    if not np.isfinite(color).all():

        print(
            "WARNING: Invalid pixels in frame",
            i
        )


    frames.append(color)


    # --------------------------------------------------------
    # SAVE PREVIEW
    # --------------------------------------------------------

    if i == 0:

        preview_path = os.path.join(
            preview_directory,
            "combined_preview.png"
        )

        imageio.imwrite(
            preview_path,
            color
        )

        print()
        print("Preview saved:")
        print(preview_path)


    # --------------------------------------------------------
    # SAVE MIDDLE FRAME
    # --------------------------------------------------------

    if i == total_frames // 2:

        middle_preview_path = os.path.join(
            preview_directory,
            "combined_middle.png"
        )

        imageio.imwrite(
            middle_preview_path,
            color
        )

        print()
        print("Middle preview saved:")
        print(middle_preview_path)


    # --------------------------------------------------------
    # PROGRESS
    # --------------------------------------------------------

    if (
        i % 10 == 0
        or i == total_frames - 1
    ):

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

print()
print("=" * 60)
print("SAVING GIF")
print("=" * 60)


imageio.mimsave(
    OUTPUT_FILE,
    frames,
    fps=FPS,
    loop=0
)


# ============================================================
# VERIFY GIF
# ============================================================

if not os.path.exists(OUTPUT_FILE):

    print()
    print("ERROR: GIF was not created.")
    sys.exit(1)


file_size = os.path.getsize(
    OUTPUT_FILE
)


print()
print("GIF created successfully.")
print("File size:", file_size, "bytes")


if file_size < 1000:

    print(
        "WARNING: GIF file is unusually small."
    )


# ============================================================
# COMPLETE
# ============================================================

print()
print("=" * 60)
print("RENDERING COMPLETE")
print("=" * 60)

print("Frames :", total_frames)
print("GIF    :", OUTPUT_FILE)

print(
    "Preview:",
    os.path.join(
        preview_directory,
        "combined_preview.png"
    )
)

print(
    "Middle :",
    os.path.join(
        preview_directory,
        "combined_middle.png"
    )
)

print("=" * 60)