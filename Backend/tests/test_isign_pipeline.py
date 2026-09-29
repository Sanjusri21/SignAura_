"""
Bridge test file linking to tests/test_isign_pipeline.py.
"""

from tests.test_isign_pipeline import (
    test_hf_authentication_failure,
    test_dataset_search,
    test_uid_lookup,
    test_pose_retrieval,
    test_pose_integrity,
    test_smplx_output_shape,
    test_nan_inf_checks,
    test_cache_hit_behavior,
)
