"""
Autonomous Offline Master Runner for Numbers Dataset
1. Executes:
   - Group Numbers (Numbers-20261128T020758Z-1-001.zip: 43 videos)
2. Auto-cleans staging files after processing.
3. Automatically re-indexes all signs into bridgeconn.db.
Works 100% locally and offline without internet.
"""

import os
import sys
import subprocess

REPO_ROOT = r"c:\Users\Admin\Desktop\Sign\sign3"
SCRIPTS_DIR = os.path.join(REPO_ROOT, "Backend", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from process_group_letter import process_entire_letter

PYTHON_EXE = r"D:\SignAuraData\venv_mediapipe\Scripts\python.exe"


def main():
    print("=======================================================", flush=True)
    print("AUTONOMOUS MASTER CHAIN RUNNER (NUMBERS DATASET)", flush=True)
    print("=======================================================\n", flush=True)

    print("\n" + "#" * 65, flush=True)
    print(">>> LAUNCHING AUTONOMOUS GROUP NUMBERS EXTRACTION <<<", flush=True)
    print("#" * 65 + "\n", flush=True)
    try:
        process_entire_letter("Numbers", workers=4)
        print("\n[SUCCESS] Group Numbers extraction completed 100%!", flush=True)
    except Exception as e:
        print(f"[ERROR] Group Numbers encountered an error: {e}", flush=True)

    # Final Step: Re-index all into database
    print("\n[INDEX] Re-indexing all signs into bridgeconn.db...", flush=True)
    try:
        idx_script = os.path.join(SCRIPTS_DIR, "index_backend_datasets.py")
        subprocess.run([PYTHON_EXE, idx_script], check=True)
        print("[SUCCESS] All signs indexed into master database!", flush=True)
    except Exception as e:
        print(f"[WARNING] Database indexing failed: {e}", flush=True)

    print("\n=======================================================", flush=True)
    print("NUMBERS GROUP COMPLETED AUTONOMOUSLY!", flush=True)
    print("=======================================================\n", flush=True)


if __name__ == "__main__":
    main()

