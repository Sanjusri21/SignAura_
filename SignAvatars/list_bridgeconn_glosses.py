"""
BridgeConn ISL Gloss Inventory Scanner.
Enumerates available lexical gloss items and metadata from the BridgeConn WebDataset shards
without loading full video files or overloading memory.
Generates outputs/bridgeconn_gloss_inventory.json.
"""

import os
import sys
import json
import re
from pathlib import Path
import webdataset as wds

BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
INVENTORY_FILE = OUTPUTS_DIR / "bridgeconn_gloss_inventory.json"

DATASET_SHARDS = [
    "https://huggingface.co/datasets/bridgeconn/sign-dictionary-isl/resolve/main/shard_00001-train.tar",
    "https://huggingface.co/datasets/bridgeconn/sign-dictionary-isl/resolve/main/shard_00002-train.tar",
    "https://huggingface.co/datasets/bridgeconn/sign-dictionary-isl/resolve/main/shard_00003-train.tar",
    "https://huggingface.co/datasets/bridgeconn/sign-dictionary-isl/resolve/main/shard_00004-train.tar",
    "https://huggingface.co/datasets/bridgeconn/sign-dictionary-isl/resolve/main/shard_00005-train.tar",
    "https://huggingface.co/datasets/bridgeconn/sign-dictionary-isl/resolve/main/shard_00006-train.tar",
    "https://huggingface.co/datasets/bridgeconn/sign-dictionary-isl/resolve/main/shard_00007-train.tar"
]


def extract_gloss_from_json(json_data):
    if isinstance(json_data, bytes):
        json_data = json.loads(json_data.decode("utf-8", errors="replace"))
    elif isinstance(json_data, str):
        json_data = json.loads(json_data)

    if not isinstance(json_data, dict):
        return str(json_data)

    transcript = json_data.get("transcript")
    if isinstance(transcript, dict):
        return transcript.get("text") or transcript.get("gloss") or ""
    elif isinstance(transcript, str):
        return transcript

    return (
        json_data.get("gloss")
        or json_data.get("word")
        or json_data.get("text")
        or json_data.get("filename")
        or ""
    )


def scan_shards(max_shards=2, max_samples_per_shard=250):
    print("=" * 60)
    print("SCANNING BRIDGECONN ISL GLOSS INVENTORY")
    print("=" * 60)

    inventory = []
    seen_glosses = set()
    total_scanned = 0

    for shard_idx, shard_url in enumerate(DATASET_SHARDS[:max_shards], 1):
        shard_name = f"shard_{shard_idx:05d}-train.tar"
        print(f"\nScanning Shard {shard_idx}/{max_shards}: {shard_name} ...")

        try:
            dataset = wds.WebDataset(shard_url, shardshuffle=False).decode()
            shard_count = 0

            for sample in dataset:
                shard_count += 1
                total_scanned += 1

                json_raw = sample.get("json", {})
                raw_gloss = extract_gloss_from_json(json_raw)
                has_pose = "pose-mediapipe.pose" in sample or "pose-dwpose.npz" in sample

                clean_gloss = str(raw_gloss).strip()
                normalized_gloss = re.sub(r"\s*\(\d+\)", "", clean_gloss).strip().lower()

                key_name = sample.get("__key__", f"sample_{total_scanned}")

                item = {
                    "gloss": clean_gloss,
                    "normalized": normalized_gloss,
                    "key": key_name,
                    "shard": shard_name,
                    "shard_index": shard_count - 1,
                    "available": True,
                    "pose_available": bool(has_pose),
                    "formats": [k for k in sample.keys() if not k.startswith("__")]
                }

                inventory.append(item)
                seen_glosses.add(normalized_gloss)

                if shard_count >= max_samples_per_shard:
                    print(f"  Reached sample limit ({max_samples_per_shard}) for {shard_name}")
                    break

        except Exception as e:
            print(f"  Error reading {shard_name}: {e}")
            continue

    result = {
        "source": "BridgeConn Sign Dictionary ISL",
        "total_glosses": len(inventory),
        "unique_normalized_glosses": len(seen_glosses),
        "shards_scanned": min(max_shards, len(DATASET_SHARDS)),
        "glosses": inventory
    }

    with open(INVENTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("\n" + "=" * 60)
    print(f"INVENTORY SCAN COMPLETE: {len(inventory)} total entries, {len(seen_glosses)} unique glosses")
    print(f"Saved to: {INVENTORY_FILE}")
    print("=" * 60)
    return result


if __name__ == "__main__":
    scan_shards(max_shards=2, max_samples_per_shard=300)
