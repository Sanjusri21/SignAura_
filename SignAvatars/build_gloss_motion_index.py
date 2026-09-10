import json
import re
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATASETS_DIR = BASE_DIR / "datasets"

WLASL_FILE = DATASETS_DIR / "word2motion" / "WLASL_v0.3.json"
HAMNOSYS_FILE = DATASETS_DIR / "hamnosys2motion" / "data.json"
MOTION_INDEX_FILE = DATASETS_DIR / "motion_index.json"

OUTPUT_FILE = DATASETS_DIR / "gloss_motion_index.json"


# ============================================================
# WORD NORMALIZATION
# ============================================================

def normalize_word(value):
    """
    Normalize English/gloss text for comparison.
    """

    if value is None:
        return ""

    value = str(value).strip().lower()

    # Remove HamNoSys-style ^ suffixes
    value = value.replace("^", "")

    # Replace punctuation with spaces
    value = re.sub(r"[^a-z0-9]+", " ", value)

    # Collapse whitespace
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_type_name(value):
    """
    Convert:

        TO-DRINK1^ -> to drink
        SCHOOL3^   -> school
        YOU1^      -> you

    This is ONLY used to inspect candidates.
    It is NOT treated as proof of WLASL ↔ motion identity.
    """

    if not value:
        return ""

    value = str(value).upper().strip()

    value = value.replace("^", "")

    # Remove trailing numerical variant
    value = re.sub(r"\d+[A-Z]*$", "", value)

    # Convert separators to spaces
    value = re.sub(r"[-_]+", " ", value)

    # Remove extra whitespace
    value = re.sub(r"\s+", " ", value)

    return value.lower().strip()


# ============================================================
# LOAD JSON
# ============================================================

def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


print("=" * 60)
print("Building reliable Gloss → Motion Index")
print("=" * 60)

print()
print("Loading WLASL...")
wlasl = load_json(WLASL_FILE)

print("Loading HamNoSys2Motion...")
hamnosys = load_json(HAMNOSYS_FILE)

print("Loading motion_index...")
motion_index = load_json(MOTION_INDEX_FILE)


# ============================================================
# BASIC VALIDATION
# ============================================================

print()
print("Dataset sizes:")
print(f"  WLASL gloss entries       : {len(wlasl)}")
print(f"  HamNoSys2Motion entries  : {len(hamnosys)}")
print(f"  Motion index entries     : {len(motion_index)}")


# ============================================================
# BUILD MOTION LOOKUP TABLES
# ============================================================

# motion ID -> record
motion_by_id = {}

for motion_id, record in hamnosys.items():

    if not isinstance(record, dict):
        continue

    motion_by_id[str(motion_id)] = record


# normalized type_name -> motion IDs
type_name_to_ids = {}

for motion_id, record in motion_by_id.items():

    type_name = record.get("type_name", "")

    normalized = normalize_type_name(type_name)

    if not normalized:
        continue

    type_name_to_ids.setdefault(normalized, []).append(motion_id)


# ============================================================
# WLASL LOOKUP
# ============================================================

wlasl_by_gloss = {}

for entry in wlasl:

    if not isinstance(entry, dict):
        continue

    gloss = entry.get("gloss", "")

    normalized_gloss = normalize_word(gloss)

    if not normalized_gloss:
        continue

    wlasl_by_gloss[normalized_gloss] = entry


# ============================================================
# BUILD RESULT
# ============================================================

result = {}

resolved = 0
unresolved = 0
ambiguous = 0


for gloss, wlasl_entry in wlasl_by_gloss.items():

    original_gloss = wlasl_entry.get("gloss", gloss)

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # We do NOT assume:
    #
    # WLASL video_id == HamNoSys2Motion ID
    #
    # They are different datasets.
    # --------------------------------------------------------

    candidates = []

    # --------------------------------------------------------
    # Candidate search using type_name
    # --------------------------------------------------------

    direct_candidates = type_name_to_ids.get(gloss, [])

    for motion_id in direct_candidates:

        record = motion_by_id[motion_id]

        candidates.append({
            "motion_id": motion_id,
            "type_name": record.get("type_name"),
            "hamnosys_text": record.get("hamnosys_text"),
            "hamnosys": record.get("hamnosys"),
            "video_45": record.get("video_45"),
            "video_90": record.get("video_90"),
            "video_above": record.get("video_above"),
            "video_frontal": record.get("video_frontal"),
            "match_type": "type_name_exact"
        })

    # --------------------------------------------------------
    # If no exact match, search individual words.
    #
    # This is marked as candidate_only and NOT automatically
    # accepted as the correct mapping.
    # --------------------------------------------------------

    if not candidates:

        for motion_id, record in motion_by_id.items():

            type_name = normalize_type_name(
                record.get("type_name", "")
            )

            if not type_name:
                continue

            words = type_name.split()

            if gloss in words:

                candidates.append({
                    "motion_id": motion_id,
                    "type_name": record.get("type_name"),
                    "hamnosys_text": record.get("hamnosys_text"),
                    "hamnosys": record.get("hamnosys"),
                    "video_45": record.get("video_45"),
                    "video_90": record.get("video_90"),
                    "video_above": record.get("video_above"),
                    "video_frontal": record.get("video_frontal"),
                    "match_type": "type_name_word_candidate"
                })

    # --------------------------------------------------------
    # WLASL instances
    # --------------------------------------------------------

    instances = []

    for instance in wlasl_entry.get("instances", []):

        if not isinstance(instance, dict):
            continue

        instances.append({
            "instance_id": instance.get("instance_id"),
            "video_id": str(instance.get("video_id", "")),
            "source": instance.get("source"),
            "frame_start": instance.get("frame_start"),
            "frame_end": instance.get("frame_end"),
            "fps": instance.get("fps")
        })

    # --------------------------------------------------------
    # Determine status
    # --------------------------------------------------------

    if len(candidates) == 1:

        status = "candidate"

        # IMPORTANT:
        # We call it candidate, not verified.
        resolved += 1

    elif len(candidates) > 1:

        status = "ambiguous"
        ambiguous += 1

    else:

        status = "unresolved"
        unresolved += 1

    # --------------------------------------------------------
    # Store
    # --------------------------------------------------------

    result[gloss] = {
        "gloss": original_gloss,

        "status": status,

        "wlasl_instances": instances,

        "motion_candidates": candidates,

        "mapping_note": (
            "Candidate generated from HamNoSys2Motion type_name. "
            "WLASL video_id and HamNoSys2Motion motion_id are not "
            "assumed to be identical."
        )
    }


# ============================================================
# SAVE
# ============================================================

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

    json.dump(
        result,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# PRINT SUMMARY
# ============================================================

print()
print("=" * 60)
print("Gloss → Motion Index created")
print("=" * 60)

print(f"Total WLASL glosses : {len(result)}")
print(f"Candidates          : {resolved}")
print(f"Ambiguous           : {ambiguous}")
print(f"Unresolved          : {unresolved}")

print()
print(f"Output: {OUTPUT_FILE}")

# ============================================================
# TEST WORDS
# ============================================================

test_words = [
    "hello",
    "book",
    "help",
    "eat",
    "drink",
    "school",
    "home",
    "you",
    "thank"
]

print()
print("=" * 60)
print("TEST WORDS")
print("=" * 60)

for word in test_words:

    key = normalize_word(word)

    print()
    print(f"{word}:")

    if key not in result:

        print("   WLASL gloss: NOT FOUND")
        continue

    item = result[key]

    print(f"   Status: {item['status']}")

    print(
        f"   WLASL instances: "
        f"{len(item['wlasl_instances'])}"
    )

    candidates = item["motion_candidates"]

    if not candidates:

        print("   Motion candidates: NONE")

    else:

        for candidate in candidates[:10]:

            print(
                f"   {candidate['motion_id']} "
                f"=> {candidate['type_name']} "
                f"[{candidate['match_type']}]"
            )

        if len(candidates) > 10:

            print(
                f"   ... and "
                f"{len(candidates) - 10} more candidates"
            )


print()
print("=" * 60)
print("DONE")
print("=" * 60)