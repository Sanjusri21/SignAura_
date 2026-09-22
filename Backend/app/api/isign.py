"""
iSign Benchmark Dataset FastAPI Router.
Provides endpoints for search, exact UID lookup, and sentence matching against iSign benchmark.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional

from app.services.isign import (
    isign_metadata,
    isign_inspector,
    ISignItem,
    ISignMatchRequest,
    ISignSentenceResponse,
)
from app.services.isign_sentence_service import isign_sentence_service

router = APIRouter(
    prefix="/isign",
    tags=["iSign Benchmark Dataset"]
)


@router.get("/status")
async def get_isign_dataset_status() -> Dict[str, Any]:
    """
    Returns current configuration, paths, archive status, and record count for iSign.
    """
    overview = isign_inspector.get_dataset_overview()
    overview["total_indexed_records"] = isign_metadata.total_count
    return overview


@router.get("/search/{query}")
async def search_isign_entries(
    query: str,
    limit: int = Query(default=10, ge=1, le=50)
) -> Dict[str, Any]:
    """
    Searches iSign metadata by sentence or phrase using fuzzy token matching.
    """
    clean_query = query.strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    results = isign_metadata.search_by_text(clean_query, limit=limit)
    items = []
    for item, score in results:
        items.append({
            "uid": item.uid,
            "video_id": item.video_id,
            "sequence_number": item.sequence_number,
            "text": item.text,
            "split": item.split,
            "source": item.source,
            "similarity_score": score,
            "pose_available": item.pose_available,
            "video_available": item.video_available,
        })

    return {
        "query": clean_query,
        "count": len(items),
        "results": items
    }


@router.get("/item/{uid}")
async def get_isign_item_by_uid(uid: str) -> Dict[str, Any]:
    """
    Retrieves exact iSign benchmark record by UID.
    Returns 404 if the UID is not found.
    """
    item = isign_metadata.get_by_uid(uid)
    if not item:
        raise HTTPException(
            status_code=404,
            detail=f"iSign item with UID '{uid}' not found in benchmark metadata."
        )

    return {
        "uid": item.uid,
        "video_id": item.video_id,
        "sequence_number": item.sequence_number,
        "text": item.text,
        "split": item.split,
        "source": item.source,
        "pose_available": item.pose_available,
        "video_available": item.video_available,
        "direct_smplx_available": False,
        "license": "CC BY-NC-SA 4.0",
    }


@router.post("/match", response_model=ISignSentenceResponse)
async def match_isign_sentence(req: ISignMatchRequest) -> ISignSentenceResponse:
    """
    Matches an input English sentence against the iSign benchmark dataset,
    identifies component signs, checks BridgeConn 3D availability, and reports
    available vs missing signs with zero fake substitutions.
    """
    return await isign_sentence_service.resolve_sentence(req.text)
