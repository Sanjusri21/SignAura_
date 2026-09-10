import json
import os
import pickle

HAMNOSYS_FILE = r".\datasets\hamnosys2motion\data.json"
MOTION_DIR = r"C:\Users\sanju\Downloads\hamnosys_pkls_default_shape\hamnosys_pkls_default_shape"
OUTPUT_FILE = r".\datasets\motion_index.json"


print("Loading HamNoSys data...")

with open(HAMNOSYS_FILE, "r", encoding="utf-8") as f:
    hamnosys_data = json.load(f)

print("HamNoSys entries:", len(hamnosys_data))


index = {}

for motion_id, data in hamnosys_data.items():

    pkl_file = os.path.join(
        MOTION_DIR,
        motion_id + ".pkl"
    )

    if not os.path.exists(pkl_file):
        continue

    index[motion_id] = {
        "motion_id": motion_id,
        "hamnosys": data.get("hamnosys"),
        "hamnosys_text": data.get("hamnosys_text"),
        "type_name": data.get("type_name"),
        "pkl": pkl_file
    }


print("Matched motion files:", len(index))


os.makedirs(
    os.path.dirname(OUTPUT_FILE),
    exist_ok=True
)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(
        index,
        f,
        ensure_ascii=False,
        indent=2
    )

print("Saved:", OUTPUT_FILE)