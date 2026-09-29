"""
Dataset Ingestion and Adapter Layer for SignAura.
Modules:
- bridgeconn: BridgeConn dataset adapter for curated isolated-sign ingestion
- isign: iSign continuous sign-motion research and retrieval adapter
"""

from .bridgeconn import BridgeConnDatasetAdapter, ingest_bridgeconn_sign
from .isign import ISignDatasetAdapter, get_isign_adapter

__all__ = [
    "BridgeConnDatasetAdapter",
    "ingest_bridgeconn_sign",
    "ISignDatasetAdapter",
    "get_isign_adapter",
]
