"""
Continuous Offline Master Runner:
Chains: Wait for B to finish -> Run Group C -> Run Group D.
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


def is_group_b_running():
    try:
        # Check tasklist for python processes running process_group_b_archive
        cmd = 'powershell -Command "Get-CimInstance Win32_Process -Filter \\"Name like \'%python%\'\\" | Select-Object -ExpandProperty CommandLine"'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        lines = res.stdout.splitlines()
        for line in lines:
            if "process_group_b_archive.py" in line:
                return True
    except Exception:
        pass
    return False


def wait_for_group_b():
    print("=======================================================")
    print("AUTONOMOUS MASTER CHAIN RUNNER (B -> C -> D)")
    print("=======================================================")
    print("[WAIT] Monitoring Group B extraction...")

    while True:
        running = is_group_b_running()
        if not running:
            # Double check after 5 seconds to ensure it did not just switch archives
            time.sleep(5)
            if not is_group_b_running():
                print("\n[COMPLETE] Group B extraction has officially finished!")
                break
        
        # Check current signs extracted
        b_dest = os.path.join(REPO_ROOT, "Backend", "datasets", "ISL_DRIVE", "B")
        count_b = len([f for f in os.listdir(b_dest) if f.endswith(".npz")]) if os.path.exists(b_dest) else 0
        print(f"[STATUS] Group B still running... (Currently {count_b} new signs in ISL_DRIVE/B). Checking again in 30s.")
        time.sleep(30)


def main():
    # Step 1: Wait for B to finish
    wait_for_group_b()

    # Step 2: Automatically run Group C
    print("\n" + "#"*65)
    print(">>> STEP 2: AUTOMATICALLY LAUNCHING GROUP C EXTRACTION <<<")
    print("#"*65 + "\n")
    try:
        process_entire_letter("C", workers=4)
        print("\n[SUCCESS] Group C extraction completed 100%!")
    except Exception as e:
        print(f"[ERROR] Group C encountered an error: {e}")

    # Step 3: Automatically run Group D
    print("\n" + "#"*65)
    print(">>> STEP 3: AUTOMATICALLY LAUNCHING GROUP D EXTRACTION <<<")
    print("#"*65 + "\n")
    try:
        process_entire_letter("D", workers=4)
        print("\n[SUCCESS] Group D extraction completed 100%!")
    except Exception as e:
        print(f"[ERROR] Group D encountered an error: {e}")

    # Step 4: Re-index all into database
    print("\n[INDEX] Re-indexing all new signs into bridgeconn.db...")
    try:
        idx_script = os.path.join(SCRIPTS_DIR, "index_backend_datasets.py")
        subprocess.run([PYTHON_EXE, idx_script], check=True)
        print("[SUCCESS] All signs from B, C, D indexed and ready for 3D avatar!")
    except Exception as e:
        print(f"[WARNING] Database indexing failed: {e}")

    print("\n=======================================================")
    print("ALL GROUPS (B, C, AND D) HAVE COMPLETED AUTONOMOUSLY!")
    print("=======================================================\n")


if __name__ == "__main__":
    main()

