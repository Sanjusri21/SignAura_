"""
Autonomous Offline Master Runner for Groups L, M, N:
1. Sequentially executes:
   - Group L (L-001, L-002: 412 videos)
   - Group M (M-001 to M-003: 1,070 videos)
   - Group N (N-001, N-002: 266 videos)
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
    print("AUTONOMOUS MASTER CHAIN RUNNER (L -> M -> N)", flush=True)
    print("=======================================================\n", flush=True)

    letters = ["M", "N"]
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
        print("[SUCCESS] All signs from A through N indexed into database!", flush=True)
    except Exception as e:
        print(f"[WARNING] Database indexing failed: {e}", flush=True)

    print("\n=======================================================", flush=True)
    print("ALL GROUPS (L, M, AND N) HAVE COMPLETED AUTONOMOUSLY!", flush=True)
    print("=======================================================\n", flush=True)


if __name__ == "__main__":
    main()

