"""
iSign Benchmark Dataset Integration Package for SignAura.
Provides metadata-first search, resource inspection, and semantic mapping to BridgeConn.
"""

from .config import (
    ISIGN_DATA_DIR,
    ISIGN_METADATA_PATH,
    ISIGN_POSES_DIR,
    ISIGN_VIDEOS_DIR,
    ISIGN_ENABLED,
)
from .models import (
    ISignItem,
    ISignMatchResult,
    ISignGlossMapping,
    ISignSentenceResponse,
    ISignMatchRequest,
    ISignSearchRequest,
    GlossMatchClassification,
)
from .dataset import isign_inspector, ISignDatasetInspector
from .metadata import isign_metadata, ISignMetadataRepository
from .mapper import isign_mapper, ISignToBridgeConnMapper
from .hf_client import isign_hf_client, ISignHFClient
from .retrieval import (
    isign_pose_retriever,
    ISignPoseRetriever,
    ISignAuthError,
    ISignRetrievalError,
    ISignIntegrityError,
    ARCHIVE_MEMBER_REGISTRY,
)
from .motion_service import isign_motion_service, ISignMotionService

__all__ = [
    "ISIGN_DATA_DIR",
    "ISIGN_METADATA_PATH",
    "ISIGN_POSES_DIR",
    "ISIGN_VIDEOS_DIR",
    "ISIGN_ENABLED",
    "ISignItem",
    "ISignMatchResult",
    "ISignGlossMapping",
    "ISignSentenceResponse",
    "ISignMatchRequest",
    "ISignSearchRequest",
    "GlossMatchClassification",
    "isign_inspector",
    "ISignDatasetInspector",
    "isign_metadata",
    "ISignMetadataRepository",
    "isign_mapper",
    "ISignToBridgeConnMapper",
    "isign_hf_client",
    "ISignHFClient",
    "isign_pose_retriever",
    "ISignPoseRetriever",
    "ISignAuthError",
    "ISignRetrievalError",
    "ISignIntegrityError",
    "ARCHIVE_MEMBER_REGISTRY",
    "isign_motion_service",
    "ISignMotionService",
]
