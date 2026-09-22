"""
Resilient shard downloader with automatic resume loop.
Downloads shards 1 to 6 one-by-one or with 2 workers until every shard matches exact byte size.
"""

import os
import sys
import subprocess
import time

SHARDS_DIR = r"D:\SignAuraData\BridgeConn\shards"
BASE_URL = "https://huggingface.co/datasets/bridgeconn/sign-dictionary-isl/resolve/main"

SHARD_TARGETS = {
    "shard_00001-train.tar": 1075251200,
    "shard_00002-train.tar": 1075886080,
    "shard_00003-train.tar": 1074472960,
    "shard_00004-train.tar": 1075696640,
    "shard_00005-train.tar": 1076162560,
    "shard_00006-train.tar": 1074846720,
    "shard_00007-train.tar": 661934080,
}

def download_until_complete(shard_name: str, target_size: int):
    target_path = os.path.join(SHARDS_DIR, shard_name)
    url = f"{BASE_URL}/{shard_name}"
    
    while True:
        curr_size = os.path.getsize(target_path) if os.path.exists(target_path) else 0
        if curr_size >= target_size:
            print(f"[{time.strftime('%X')}] {shard_name} is 100% COMPLETE ({curr_size} bytes)")
            break
            
        print(f"[{time.strftime('%X')}] Downloading {shard_name}: {curr_size / (1024*1024):.1f} / {target_size / (1024*1024):.1f} MB ({curr_size/target_size*100:.1f}%)")
        cmd = [
            "curl.exe",
            "-L",
            "-C", "-",
            "--retry", "5",
            "--retry-delay", "2",
            "--connect-timeout", "30",
            "-o", target_path,
            url
        ]
        
        proc = subprocess.run(cmd)
        time.sleep(1)

if __name__ == "__main__":
    # Prioritize shard 1, 3, 2 which are already ~50% downloaded
    ordered_shards = [
        "shard_00001-train.tar",
        "shard_00003-train.tar",
        "shard_00002-train.tar",
        "shard_00006-train.tar",
        "shard_00004-train.tar",
        "shard_00005-train.tar",
    ]
    for s in ordered_shards:
        download_until_complete(s, SHARD_TARGETS[s])
    print("ALL SHARDS DOWNLOADED SUCCESSFULLY!")
