"""
Pydantic schemas and models for iSign Benchmark Dataset.
Uses actual dataset fields discovered during research:
- uid: [video_id]-[sequence_number]
- video_id: hash of video
- sequence_number: segment index
- text: English translation text
- split: train/dev/test
- source: ISLRTC/ISH/DEF
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class GlossMatchClassification(str, Enum):
    """Deterministic classification of iSign tokens against BridgeConn ISL dictionary."""
    EXACT_BRIDGECONN_MATCH = "EXACT_BRIDGECONN_MATCH"
    VARIANT_BRIDGECONN_MATCH = "VARIANT_BRIDGECONN_MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    NO_BRIDGECONN_MATCH = "NO_BRIDGECONN_MATCH"


class ISignItem(BaseModel):
    """Represents a real entry in iSign_v1.1.csv."""
    uid: str = Field(..., description="Unique Identifier: [video_id]-[sequence_number]")
    video_id: str = Field(..., description="Source video identifier")
    sequence_number: int = Field(..., description="Segment order within the video")
    text: str = Field(..., description="English sentence/phrase translation")
    split: str = Field(..., description="train, dev, or test")
    source: str = Field(..., description="ISLRTC, ISH, or DEF")
    pose_available: bool = Field(default=False, description="Whether .pose or .npz keypoint file exists locally")
    video_available: bool = Field(default=False, description="Whether .mp4 video clip exists locally")


class ISignGlossMapping(BaseModel):
    """Component gloss mapped to BridgeConn ISL dictionary."""
    word: str = Field(..., description="Original word token")
    gloss: str = Field(..., description="Normalized uppercase gloss representation")
    classification: GlossMatchClassification = Field(..., description="Strict match status")
    bridgeconn_gloss: Optional[str] = Field(None, description="Matching BridgeConn dictionary gloss if found")
    smplx_available: bool = Field(default=False, description="Whether an SMPL-X 3D animation exists in BridgeConn")


class ISignMatchResult(BaseModel):
    """Summary of matched iSign benchmark item."""
    matched: bool = Field(default=False)
    uid: Optional[str] = None
    video_id: Optional[str] = None
    sequence_number: Optional[int] = None
    text: Optional[str] = None
    split: Optional[str] = None
    source: Optional[str] = None
    score: float = Field(default=0.0, description="Match similarity score (0.0 - 1.0)")
    pose_available: bool = Field(default=False)
    video_available: bool = Field(default=False)
    direct_smplx_available: bool = Field(
        default=False,
        description="False until a validated continuous iSign pose -> SMPL-X pipeline is implemented"
    )


class ISignSentenceResponse(BaseModel):
    """Standardized response model for sentence/phrase matching in SignAura."""
    available: bool = Field(..., description="True if an iSign benchmark item was matched")
    input_text: str = Field(..., description="The original user query text")
    isign_match: Optional[ISignMatchResult] = None
    glosses: List[str] = Field(default_factory=list, description="Extracted ISL gloss tokens")
    bridgeconn_matches: List[ISignGlossMapping] = Field(default_factory=list, description="Mapping per gloss")
    available_signs: List[str] = Field(default_factory=list, description="BridgeConn signs verified present")
    missing_signs: List[str] = Field(default_factory=list, description="Signs absent from BridgeConn")
    animation_available: bool = Field(default=False, description="True ONLY if full 3D animation can be generated")
    animation_url: Optional[str] = Field(None, description="Streaming URL if animation is available")
    source: str = Field(default="iSign Benchmark + BridgeConn ISL")
    message: str = Field(..., description="Truthful diagnostic message regarding animation and mapping status")


class ISignSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Query text or phrase to search")
    limit: int = Field(default=10, ge=1, le=50)


class ISignMatchRequest(BaseModel):
    text: str = Field(..., min_length=1, description="English sentence to match against iSign benchmark")
