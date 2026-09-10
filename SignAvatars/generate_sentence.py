import os
import sys
import subprocess
import numpy as np

from motion_transform import convert_and_normalize_vertices

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MOTION_DIR = r"C:\Users\sanju\Downloads\hamnosys_pkls_default_shape\hamnosys_pkls_default_shape"

OUTPUT_NPY_DIR = os.path.join(
    BASE_DIR,
    "outputs",
    "npy"
)

OUTPUT_GIF_DIR = os.path.join(
    BASE_DIR,
    "outputs",
    "gifs"
)

# ============================================================
# VERIFIED ENGLISH -> SIGNAVATAR MOTION MAPPINGS
# ============================================================

WORD_TO_MOTION = {
    "welcome": "9310",
    "help": "13847",
    "you": "8597",
    "book": "10648",
    "drink": "3354",
    "home": "73060",
    "eat": "13123",
}

# ============================================================
# TERMINAL OUTPUT HELPER
# ============================================================

def safe_print(text=""):
    """
    Print safely on Windows even when the terminal uses cp1252.
    """
    try:
        print(text)
    except UnicodeEncodeError:
        print(
            str(text).encode(
                "ascii",
                errors="replace"
            ).decode("ascii")
        )


# ============================================================
# CHECK ARGUMENT
# ============================================================

if len(sys.argv) < 2:

    safe_print()
    safe_print("=" * 60)
    safe_print("SIGNAVATAR SENTENCE GENERATOR")
    safe_print("=" * 60)
    safe_print()
    safe_print("Usage:")
    safe_print('  python generate_sentence.py "welcome help you"')
    safe_print()
    sys.exit(1)


# ============================================================
# READ SENTENCE
# ============================================================

sentence = " ".join(sys.argv[1:]).strip()

if not sentence:
    safe_print("ERROR: Empty sentence.")
    sys.exit(1)


words = sentence.lower().split()


# ============================================================
# HEADER
# ============================================================

safe_print("=" * 60)
safe_print("SIGNAVATAR SENTENCE GENERATOR")
safe_print("=" * 60)

safe_print(f"Sentence: {sentence}")
safe_print()


# ============================================================
# WORD -> MOTION
# ============================================================

motion_ids = []
unknown_words = []

for word in words:

    if word in WORD_TO_MOTION:

        motion_id = WORD_TO_MOTION[word]

        safe_print(
            f"{word:<15} -> Motion ID {motion_id}"
        )

        motion_ids.append(
            (word, motion_id)
        )

    else:

        safe_print(
            f"{word:<15} -> NOT FOUND"
        )

        unknown_words.append(word)


# ============================================================
# CHECK UNKNOWN WORDS
# ============================================================

if unknown_words:

    safe_print()
    safe_print("=" * 60)
    safe_print("ERROR: UNKNOWN WORDS")
    safe_print("=" * 60)

    for word in unknown_words:
        safe_print(f" - {word}")

    safe_print()
    safe_print("Currently supported words:")

    for word in WORD_TO_MOTION:
        safe_print(f" - {word}")

    sys.exit(1)


# ============================================================
# CREATE OUTPUT DIRECTORIES
# ============================================================

os.makedirs(
    OUTPUT_NPY_DIR,
    exist_ok=True
)

os.makedirs(
    OUTPUT_GIF_DIR,
    exist_ok=True
)


# ============================================================
# LOAD MOTIONS
# ============================================================

safe_print()
safe_print("=" * 60)
safe_print("LOADING MOTIONS")
safe_print("=" * 60)

all_vertices = []


for word, motion_id in motion_ids:

    npy_file = os.path.join(
        OUTPUT_NPY_DIR,
        f"{motion_id}.npy"
    )

    # --------------------------------------------------------
    # Generate vertices if missing
    # --------------------------------------------------------

    if not os.path.exists(npy_file):

        safe_print()
        safe_print(
            f"Vertices not found for {word} ({motion_id})"
        )

        safe_print("Generating vertices...")

        test_motion_path = os.path.join(
            BASE_DIR,
            "test_motion.py"
        )

        if not os.path.exists(test_motion_path):

            safe_print(
                "ERROR: test_motion.py not found."
            )

            sys.exit(1)

        result = subprocess.run(
            [
                sys.executable,
                test_motion_path,
                motion_id
            ],
            cwd=BASE_DIR,
            check=False
        )

        if result.returncode != 0:

            safe_print(
                f"ERROR: Could not generate motion {motion_id}"
            )

            sys.exit(1)

        generated_file = os.path.join(
            BASE_DIR,
            f"signavatar_{motion_id}_vertices.npy"
        )

        if os.path.exists(generated_file):

            np.save(
                npy_file,
                np.load(generated_file)
            )

            safe_print(
                f"Created: {npy_file}"
            )

        else:

            safe_print(
                f"ERROR: Generated vertices file not found:"
            )

            safe_print(
                generated_file
            )

            sys.exit(1)


    # --------------------------------------------------------
    # Verify NPY file
    # --------------------------------------------------------

    if not os.path.exists(npy_file):

        safe_print(
            f"ERROR: Missing vertices file: {npy_file}"
        )

        sys.exit(1)


    # --------------------------------------------------------
    # Load vertices
    # --------------------------------------------------------

    try:

        vertices = np.load(
            npy_file
        )

    except Exception as e:

        safe_print(
            f"ERROR: Could not load {npy_file}"
        )

        safe_print(
            str(e)
        )

        sys.exit(1)


    # --------------------------------------------------------
    # Validate shape
    # --------------------------------------------------------

    if vertices.ndim != 3:

        safe_print(
            f"ERROR: Invalid vertex shape for {motion_id}: "
            f"{vertices.shape}"
        )

        sys.exit(1)


    safe_print(
        f"{word:<15} -> {motion_id} -> {vertices.shape}"
    )

    all_vertices.append(
        vertices
    )


# ============================================================
# CHECK MOTIONS
# ============================================================

if not all_vertices:

    safe_print(
        "ERROR: No motions loaded."
    )

    sys.exit(1)


# ============================================================
# COMBINE MOTIONS
# ============================================================

safe_print()
safe_print("=" * 60)
safe_print("COMBINING MOTIONS")
safe_print("=" * 60)

try:

    combined = np.concatenate(
        all_vertices,
        axis=0
    )

except Exception as e:

    safe_print(
        "ERROR: Could not combine motions."
    )

    safe_print(
        str(e)
    )

    sys.exit(1)


safe_print(
    f"Combined shape: {combined.shape}"
)

combined = convert_and_normalize_vertices(combined)


# ============================================================
# OUTPUT FILE NAME
# ============================================================

safe_name = "_".join(words)

output_npy = os.path.join(
    OUTPUT_NPY_DIR,
    f"{safe_name}.npy"
)

output_gif = os.path.join(
    OUTPUT_GIF_DIR,
    f"{safe_name}.gif"
)


# ============================================================
# SAVE COMBINED NPY
# ============================================================

try:

    np.save(
        output_npy,
        combined.astype(np.float32, copy=False)
    )

except Exception as e:

    safe_print(
        "ERROR: Could not save combined NPY."
    )

    safe_print(
        str(e)
    )

    sys.exit(1)


safe_print()
safe_print("Saved combined vertices:")
safe_print(output_npy)


# ============================================================
# RENDER GIF
# ============================================================

safe_print()
safe_print("=" * 60)
safe_print("RENDERING FINAL ANIMATION")
safe_print("=" * 60)


render_script = os.path.join(
    BASE_DIR,
    "render_combined.py"
)


if not os.path.exists(render_script):

    safe_print(
        "ERROR: render_combined.py not found."
    )

    sys.exit(1)


result = subprocess.run(
    [
        sys.executable,
        render_script,
        output_npy,
        output_gif
    ],
    cwd=BASE_DIR,
    check=False
)


# ============================================================
# CHECK RENDER RESULT
# ============================================================

if result.returncode != 0:

    safe_print()
    safe_print(
        "ERROR: Rendering failed."
    )

    sys.exit(1)


# ============================================================
# VERIFY GIF
# ============================================================

if not os.path.exists(output_gif):

    safe_print()
    safe_print(
        "ERROR: GIF was not created."
    )

    sys.exit(1)


# ============================================================
# FINAL OUTPUT
# ============================================================

safe_print()
safe_print("=" * 60)
safe_print("SENTENCE GENERATION COMPLETE")
safe_print("=" * 60)

safe_print(
    f"Sentence : {sentence}"
)

safe_print(
    f"Words    : {len(words)}"
)

safe_print(
    f"Frames   : {len(combined)}"
)

safe_print(
    f"NPY      : {output_npy}"
)

safe_print(
    f"GIF      : {output_gif}"
)

safe_print("=" * 60)

sys.exit(0)