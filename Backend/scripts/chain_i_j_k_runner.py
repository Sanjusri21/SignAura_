"""
Autonomous Offline Master Runner for Groups I, J, K:
1. Sequentially executes:
   - Group I (I-001, I-002: 351 videos)
   - Group J (J-001: 105 videos)
   - Group K (K-001: 101 videos)
2. Auto-cleans staging files archive-by-archive.
3. Automatically re-indexes all signs into bridgeconn.db.
Works 100% locally and offline without internet.
"""

import os
import sys
import time
import subprocess

REPO_ROOT = r"c:\Users\Admin\Desktop\Sign\sign3"
SCRIPTS_DIR = os.path.join(REPO_ROOT, "Backend", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from process_group_letter import process_entire_letter

PYTHON_EXE = r"D:\SignAuraData\venv_mediapipe\Scripts\python.exe"


def main():
    print("=======================================================", flush=True)
    print("AUTONOMOUS MASTER CHAIN RUNNER (I -> J -> K)", flush=True)
    print("=======================================================\n", flush=True)

    letters = ["I", "J", "K"]
    for letter in letters:
        print("\n" + "#" * 65, flush=True)
        print(f">>> LAUNCHING AUTONOMOUS GROUP {letter} EXTRACTION <<<", flush=True)
        print("#" * 65 + "\n", flush=True)
        try:
            process_entire_letter(letter, workers=4)
            print(f"\n[SUCCESS] Group {letter} extraction completed 100%!", flush=True)
        except Exception as e:
            print(f"[ERROR] Group {letter} encountered an error: {e}", flush=True)

    # Final Step: Re-index all into database
    print("\n[INDEX] Re-indexing all new signs into bridgeconn.db...", flush=True)
    try:
        idx_script = os.path.join(SCRIPTS_DIR, "index_backend_datasets.py")
        subprocess.run([PYTHON_EXE, idx_script], check=True)
        print("[SUCCESS] All signs from A through K indexed into database!", flush=True)
    except Exception as e:
        print(f"[WARNING] Database indexing failed: {e}", flush=True)

    print("\n=======================================================", flush=True)
    print("ALL GROUPS (I, J, AND K) HAVE COMPLETED AUTONOMOUSLY!", flush=True)
    print("=======================================================\n", flush=True)


if __name__ == "__main__":
    main()

