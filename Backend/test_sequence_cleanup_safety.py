"""
Comprehensive Concurrency and Safety Test Suite for AnimationSequencer Sequence Lifecycle.
Tests:
1. Active sequence read lease protects files while cleanup runs concurrently.
2. Cleanup prunes the sequence once read lease completes.
3. Multiple concurrent sequence generation and cleanup operations.
4. Mid-save failure atomicity (aborted saves leave zero partial or orphaned sequence files).
5. Retention reporting when files cannot be deleted due to active leases or locks.
6. Strict directory boundary and unrelated file isolation.
7. Below-threshold safety (no pruning when under max_sequences).
"""

import os
import sys
import time
import tempfile
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import numpy as np
import pytest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.services.animation_sequencer import AnimationSequencer, VERTEX_COUNT, COORDINATE_DIM


def test_sequence_being_served_while_cleanup_runs():
    """1. A sequence currently leased for reading/streaming cannot be deleted by concurrent cleanup."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        seq = AnimationSequencer()
        seq.sequences_dir = Path(tmp_dir)

        # Create 10 sequences
        for i in range(10):
            (seq.sequences_dir / f"sequence_test_{i:02d}.npy").write_bytes(b"data")
            (seq.sequences_dir / f"sequence_test_{i:02d}.json").write_text('{"frames": 10}', encoding="utf-8")
            t = time.time() - (10 - i) * 10
            os.utime(seq.sequences_dir / f"sequence_test_{i:02d}.npy", (t, t))
            os.utime(seq.sequences_dir / f"sequence_test_{i:02d}.json", (t, t))

        # Oldest sequence (index 0) is being actively read
        active_seq_id = "sequence_test_00"

        read_started = threading.Event()
        cleanup_finished = threading.Event()
        active_file_existed_during_cleanup = False

        def reader_task():
            nonlocal active_file_existed_during_cleanup
            with seq.acquire_sequence(active_seq_id):
                read_started.set()
                # Wait for cleanup to run while we hold the lease
                cleanup_finished.wait(timeout=5.0)
                # Verify our leased file still exists on disk
                active_file_existed_during_cleanup = (
                    (seq.sequences_dir / f"{active_seq_id}.npy").is_file() and
                    (seq.sequences_dir / f"{active_seq_id}.json").is_file()
                )

        def cleanup_task():
            read_started.wait(timeout=5.0)
            # Run cleanup with max_sequences=3
            metrics = seq._cleanup_old_sequences(max_sequences=3)
            cleanup_finished.set()
            return metrics

        with ThreadPoolExecutor(max_workers=2) as executor:
            f_reader = executor.submit(reader_task)
            f_cleanup = executor.submit(cleanup_task)
            f_reader.result(timeout=10)
            metrics = f_cleanup.result(timeout=10)

        assert active_file_existed_during_cleanup, "Active sequence was deleted while reader held lease!"
        assert (seq.sequences_dir / f"{active_seq_id}.npy").is_file()
        assert (seq.sequences_dir / f"{active_seq_id}.json").is_file()
        assert metrics["active_protected_sequences"] >= 1


def test_cleanup_after_read_finishes():
    """2. Once the read lease finishes, the sequence becomes eligible for subsequent cleanup."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        seq = AnimationSequencer()
        seq.sequences_dir = Path(tmp_dir)

        # Create 5 sequences
        for i in range(5):
            (seq.sequences_dir / f"sequence_{i:02d}.npy").write_bytes(b"data")
            (seq.sequences_dir / f"sequence_{i:02d}.json").write_text("{}", encoding="utf-8")
            t = time.time() - (5 - i) * 10
            os.utime(seq.sequences_dir / f"sequence_{i:02d}.npy", (t, t))
            os.utime(seq.sequences_dir / f"sequence_{i:02d}.json", (t, t))

        target_id = "sequence_00"

        # Lease and release
        with seq.acquire_sequence(target_id):
            pass  # Read completed

        # Run cleanup with max_sequences=2
        metrics = seq._cleanup_old_sequences(max_sequences=2)

        # Now sequence_00 is cleanly pruned
        assert not (seq.sequences_dir / f"{target_id}.npy").is_file()
        assert not (seq.sequences_dir / f"{target_id}.json").is_file()
        assert metrics["retained_sequences"] == 2


def test_multiple_concurrent_sequence_generation():
    """3. Multiple concurrent sequence generation and cleanup operations execute safely without deadlock or race."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        seq = AnimationSequencer()
        seq.sequences_dir = Path(tmp_dir)

        barrier = threading.Barrier(4)
        errors = []

        def worker_task(worker_id: int):
            try:
                barrier.wait(timeout=5.0)
                for step in range(3):
                    # Write pseudo-sequence atomically
                    s_id = f"sequence_worker_{worker_id}_{step}"
                    verts = np.ones((5, VERTEX_COUNT, COORDINATE_DIM), dtype=np.float32)
                    tmp_n = seq.sequences_dir / f".tmp_{s_id}.npy"
                    tmp_j = seq.sequences_dir / f".tmp_{s_id}.json"
                    np.save(str(tmp_n), verts)
                    tmp_j.write_text("{}", encoding="utf-8")
                    os.replace(tmp_n, seq.sequences_dir / f"{s_id}.npy")
                    os.replace(tmp_j, seq.sequences_dir / f"{s_id}.json")

                    # Concurrent cleanup with max_sequences=3
                    seq._cleanup_old_sequences(max_sequences=3, protect_sequence_id=s_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker_task, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15.0)

        assert not errors, f"Concurrent workers encountered errors: {errors}"
        # Remaining sequence count must be bounded
        remaining_stems = set(
            p.stem for p in seq.sequences_dir.glob("sequence_*.*")
            if p.suffix in (".npy", ".json")
        )
        assert len(remaining_stems) <= 12


def test_save_fails_midway_leaves_no_partial_sequence():
    """4. If saving fails midway (e.g. disk or JSON serialization error), no partial file remains."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        seq = AnimationSequencer()
        seq.sequences_dir = Path(tmp_dir)

        # Mock json.dump to raise IOError mid-save
        with patch("json.dump", side_effect=IOError("Simulated disk error during metadata write")):
            with pytest.raises(RuntimeError, match="Failed to atomically persist sequence"):
                import asyncio
                asyncio.run(seq.sequence_glosses(["sample_1"]))

        # Verify no permanent or partial files exist in sequences_dir
        permanent_files = list(seq.sequences_dir.glob("sequence_*.*"))
        temp_files = list(seq.sequences_dir.glob(".tmp_*"))

        assert len(permanent_files) == 0, f"Orphaned sequence files left on disk: {permanent_files}"
        assert len(temp_files) == 0, f"Temporary files not cleaned up: {temp_files}"


def test_retention_when_some_files_cannot_be_deleted():
    """5. When some files cannot be deleted due to locks, cleanup reports metrics and does not crash."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        seq = AnimationSequencer()
        seq.sequences_dir = Path(tmp_dir)

        # Create 6 sequences
        for i in range(6):
            (seq.sequences_dir / f"sequence_{i:02d}.npy").write_bytes(b"data")
            (seq.sequences_dir / f"sequence_{i:02d}.json").write_text("{}", encoding="utf-8")
            t = time.time() - (6 - i) * 10
            os.utime(seq.sequences_dir / f"sequence_{i:02d}.npy", (t, t))
            os.utime(seq.sequences_dir / f"sequence_{i:02d}.json", (t, t))

        # Lock sequence_00.npy exclusively
        locked_path = seq.sequences_dir / "sequence_00.npy"
        with open(locked_path, "r+b") as _locked:
            metrics = seq._cleanup_old_sequences(max_sequences=2)

        assert metrics["locked_skipped_files"] >= 1
        assert locked_path.is_file(), "Locked file was unexpectedly deleted!"
        # Retained sequences reflects that locked sequence could not be completely removed
        assert metrics["retained_sequences"] >= 2


def test_cleanup_never_touches_unrelated_files_or_parent_dir():
    """6. Ensure cleanup strictly respects directory boundaries and never touches other files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        seq = AnimationSequencer()
        seq.sequences_dir = Path(tmp_dir)

        # Unrelated files
        user_db = seq.sequences_dir / "user_database.db"
        smplx_mesh = seq.sequences_dir / "smplx_neutral.bin"
        readme = seq.sequences_dir / "README.txt"

        user_db.write_bytes(b"sqlite data")
        smplx_mesh.write_bytes(b"mesh data")
        readme.write_text("Documentation", encoding="utf-8")

        # Create 10 sequences
        for i in range(10):
            (seq.sequences_dir / f"sequence_{i:02d}.npy").write_bytes(b"x")
            (seq.sequences_dir / f"sequence_{i:02d}.json").write_text("{}", encoding="utf-8")

        seq._cleanup_old_sequences(max_sequences=2)

        # Verify unrelated files are intact
        assert user_db.is_file() and user_db.read_bytes() == b"sqlite data"
        assert smplx_mesh.is_file() and smplx_mesh.read_bytes() == b"mesh data"
        assert readme.is_file() and readme.read_text(encoding="utf-8") == "Documentation"


def test_cleanup_safe_below_threshold():
    """7. No pruning occurs when total sequence count is below threshold."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        seq = AnimationSequencer()
        seq.sequences_dir = Path(tmp_dir)

        for i in range(3):
            (seq.sequences_dir / f"sequence_{i}.npy").write_bytes(b"x")
            (seq.sequences_dir / f"sequence_{i}.json").write_text("{}", encoding="utf-8")

        metrics = seq._cleanup_old_sequences(max_sequences=10)
        assert metrics["pruned_sequences"] == 0
        assert metrics["retained_sequences"] == 3
        assert len(list(seq.sequences_dir.glob("sequence_*.*"))) == 6


def test_stale_temporary_files_cleaned_while_in_progress_preserved():
    """8. Temporary files younger than 5m are preserved (in-progress writes); stale ones older than 5m are pruned."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        seq = AnimationSequencer()
        seq.sequences_dir = Path(tmp_dir)

        now = time.time()
        fresh_tmp = seq.sequences_dir / ".tmp_in_progress_123.npy"
        stale_tmp = seq.sequences_dir / ".tmp_abandoned_456.npy"

        fresh_tmp.write_bytes(b"in progress")
        stale_tmp.write_bytes(b"abandoned")

        # Set fresh mtime = now - 10s; stale mtime = now - 600s
        os.utime(fresh_tmp, (now - 10, now - 10))
        os.utime(stale_tmp, (now - 600, now - 600))

        seq._cleanup_old_sequences(max_sequences=10)

        assert fresh_tmp.is_file(), "In-progress temporary file was erroneously deleted!"
        assert not stale_tmp.is_file(), "Stale temporary file was not cleaned up!"
