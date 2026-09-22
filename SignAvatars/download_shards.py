"""
Script to download BridgeConn shards 1 through 6 to D:\\SignAuraData\\BridgeConn\\shards.
Supports auto-resume, retry on failure, and parallel downloading.
"""

import os
import sys
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

SHARDS_DIR = r"D:\SignAuraData\BridgeConn\shards"
LOGS_DIR = r"D:\SignAuraData\BridgeConn\logs"
os.makedirs(SHARDS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

BASE_URL = "https://huggingface.co/datasets/bridgeconn/sign-dictionary-isl/resolve/main"

# Shards to download (shard 7 is already downloaded and verified)
SHARDS = [f"shard_0000{i}-train.tar" for i in range(1, 7)]

def download_shard(shard_name: str) -> bool:
    target_path = os.path.join(SHARDS_DIR, shard_name)
    url = f"{BASE_URL}/{shard_name}"
    log_path = os.path.join(LOGS_DIR, f"{shard_name}.log")
    
    print(f"[{time.strftime('%X')}] Starting download of {shard_name} -> {target_path}")
    
    cmd = [
        "curl.exe",
        "-L",
        "-C", "-",
        "--retry", "10",
        "--retry-delay", "3",
        "--retry-max-time", "600",
        "-o", target_path,
        url
    ]
    
    with open(log_path, "w", encoding="utf-8") as lf:
        proc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT)
        
    if proc.returncode == 0 and os.path.exists(target_path):
        size_mb = os.path.getsize(target_path) / (1024 * 1024)
        print(f"[{time.strftime('%X')}] Successfully completed {shard_name} ({size_mb:.2f} MB)")
        return True
    else:
        print(f"[{time.strftime('%X')}] Failed to download {shard_name} (code {proc.returncode})")
        return False

if __name__ == "__main__":
    print(f"Starting parallel download of 6 shards into {SHARDS_DIR} with 6 workers...")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(download_shard, SHARDS))
    
    success = sum(1 for r in results if r)
    print(f"Finished downloads in {time.time() - t0:.1f}s. {success}/{len(SHARDS)} shards successful.")
