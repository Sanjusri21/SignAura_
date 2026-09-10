import json
from pathlib import Path

BASE = Path(__file__).parent
DATASETS = BASE / "datasets"

with open(DATASETS / "gloss_motion_index.json", encoding="utf-8") as f:
    gloss_index = json.load(f)

with open(DATASETS / "hamnosys2motion" / "data.json", encoding="utf-8") as f:
    hamnosys = json.load(f)

words = [
    "hello",
    "book",
    "help",
    "eat",
    "drink",
    "school",
    "home",
    "you",
]

print("=" * 70)
print("VERIFYING GLOSS → MOTION CANDIDATES")
print("=" * 70)

for word in words:

    print(f"\n{'=' * 70}")
    print(f"WORD: {word.upper()}")
    print("=" * 70)

    entry = gloss_index.get(word)

    if not entry:
        print("NOT FOUND IN GLOSS INDEX")
        continue

    print("Status:", entry.get("status"))
    print("WLASL gloss:", entry.get("wlasl_gloss"))
    print("WLASL instances:", entry.get("wlasl_instance_count"))

    candidates = entry.get("motion_candidates", [])

    if not candidates:
        print("\nNO MOTION CANDIDATES")
        continue

    print("\nMOTION CANDIDATES:")

    for candidate in candidates:

        motion_id = str(candidate.get("motion_id"))

        print("\n----------------------------------------")
        print("Motion ID:", motion_id)
        print("Type name:", candidate.get("type_name"))
        print("Reason:", candidate.get("reason"))

        motion = hamnosys.get(motion_id)

        if not motion:
            print("HamNoSys entry: NOT FOUND")
            continue

        print("HamNoSys text:")
        print(motion.get("hamnosys_text"))

        print("Frontal video:")
        print(motion.get("video_frontal"))

        print("45° video:")
        print(motion.get("video_45"))

        print("90° video:")
        print(motion.get("video_90"))

print("\n")
print("=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)