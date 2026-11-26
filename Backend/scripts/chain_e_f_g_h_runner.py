"""
Continuous Offline Master Runner for Groups E, F, G, H:
1. Waits for Group D (and chain_b_c_d_runner) to complete.
2. Sequentially executes:
   - Group E (E-001 to E-003)
   - Group F (F-001 to F-003)
   - Group G (G-001 to G-002)
   - Group H (H-001 to H-002)
3. Re-indexes all signs into bridgeconn.db.
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


def is_previous_chain_running():
    try:
        cmd = 'powershell -Command "Get-CimInstance Win32_Process -Filter \\"Name like \'%python%\'\\" | Select-Object -ExpandProperty CommandLine"'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        lines = res.stdout.splitlines()
        for line in lines:
            if "chain_b_c_d_runner.py" in line:
                return True
    except Exception:
        pass
    return False


def wait_for_previous_chain():
    print("=======================================================", flush=True)
    print("AUTONOMOUS MASTER CHAIN RUNNER (E -> F -> G -> H)", flush=True)
    print("=======================================================", flush=True)
    print("[WAIT] Checking if Group D / previous chain is running...", flush=True)

    while True:
        running = is_previous_chain_running()
        if not running:
            time.sleep(10)
            if not is_previous_chain_running():
                print("\n[COMPLETE] Group D chain has officially completed!", flush=True)
                break

        # Check current signs extracted in D
        d_dest = os.path.join(REPO_ROOT, "Backend", "datasets", "ISL_DRIVE", "D")
        count_d = len([f for f in os.listdir(d_dest) if f.endswith(".npz")]) if os.path.exists(d_dest) else 0
        print(f"[STATUS] Group D still processing... (Currently {count_d} new signs in ISL_DRIVE/D). Checking again in 30s.", flush=True)
        time.sleep(30)


def main():
    # Step 1: Wait for prior chain (D) to finish
    wait_for_previous_chain()

    letters = ["E", "F", "G", "H"]
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
        print("[SUCCESS] All signs from A, B, C, D, E, F, G, H indexed into database!", flush=True)
    except Exception as e:
        print(f"[WARNING] Database indexing failed: {e}", flush=True)

    print("\n=======================================================", flush=True)
    print("ALL GROUPS (E, F, G, AND H) HAVE COMPLETED AUTONOMOUSLY!", flush=True)
    print("=======================================================\n", flush=True)


if __name__ == "__main__":
    main()

