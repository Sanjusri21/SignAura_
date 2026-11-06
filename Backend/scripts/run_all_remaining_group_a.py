"""
Sequential Processor for remaining Group A archives.
Runs A-003, then automatically continues A-004, A-005, and A-006.
Skips any .npz files that are already completed.
Cleans up temporary videos after each archive finishes.
"""

import os
import sys
import subprocess

PYTHON_EXE = r"D:\SignAuraData\venv_mediapipe\Scripts\python.exe"
SCRIPT_PATH = r"c:\Users\Admin\Desktop\Sign\sign3\Backend\scripts\process_group_a_archive.py"

ARCHIVES = [
    "A-20261104T020457Z-1-003.zip",
    "A-20261104T020457Z-1-004.zip",
    "A-20261104T020457Z-1-005.zip",
    "A-20261104T020457Z-1-006.zip"
]

def main():
    print("=======================================================")
    print("STARTING FULL SEQUENTIAL RUN FOR REMAINING GROUP A")
    print(f"Archives to process: {ARCHIVES}")
    print("=======================================================\n")

    for idx, arc in enumerate(ARCHIVES, 1):
        print(f"\n>>> [{idx}/{len(ARCHIVES)}] Starting Archive: {arc} <<<\n")
        cmd = [PYTHON_EXE, SCRIPT_PATH, "--archive", arc]
        
        # Run process and stream output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        for line in process.stdout:
            print(line, end="", flush=True)

        process.wait()
        if process.returncode != 0:
            print(f"\n[ERROR] Archive {arc} failed with exit code {process.returncode}!")
            sys.exit(process.returncode)
        else:
            print(f"\n[SUCCESS] Completed {arc}!\n")

    print("\n=======================================================")
    print("ALL GROUP A ARCHIVES (A-001 TO A-006) PROCESSED SUCCESSFULLY!")
    print("=======================================================\n")

if __name__ == "__main__":
    main()

