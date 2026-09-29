"""
iSign Benchmark Dataset FastAPI Router.
Provides authenticated endpoints for:
- Searching genuine iSign_v1.1 rows via Hugging Face Dataset Server API
- UID-targeted authentic .pose byte retrieval and SMPL-X retargeting pipeline
- Local cache inspection and metadata query
Strict zero-fabrication policy.
"""

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

from app.services.isign import (
    isign_metadata,
    isign_inspector,
    isign_hf_client,
    isign_pose_retriever,
    isign_motion_service,
    ISignAuthError,
    ISignRetrievalError,
    ISignIntegrityError,
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
    overview["cache_dir"] = str(isign_pose_retriever.cache_dir)
    return overview


@router.get("/search")
async def search_isign_by_query_param(
    q: str = Query(..., description="Search query string"),
    limit: int = Query(default=10, ge=1, le=50, description="Max results"),
) -> Dict[str, Any]:
    """
    Hugging Face Dataset Server API search endpoint:
    GET /api/isign/search?q=<query>
    Authenticated using HF_TOKEN from environment.
    Searches real iSign_v1.1 rows on Hugging Face and returns UID + text.
    No fake or generated rows.
    """
    clean_query = q.strip()
    if not clean_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'q' cannot be empty."
        )

    try:
        results = isign_hf_client.search(clean_query, limit=limit)
        return {
            "query": clean_query,
            "count": len(results),
            "results": results,
            "source": "Hugging Face Dataset Server API (Exploration-Lab/iSign)",
        }
    except ISignAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        # Fallback to local authentic metadata if network/HF server error
        logger_results = isign_metadata.search_by_text(clean_query, limit=limit)
        items = [
            {
                "uid": it.uid,
                "text": it.text,
                "split": it.split,
                "source": it.source,
            }
            for it, _ in logger_results
        ]
        if items:
            return {
                "query": clean_query,
                "count": len(items),
                "results": items,
                "source": "Local authentic iSign_v1.1 metadata cache",
            }
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Hugging Face Dataset Server API error: {e}",
        )


@router.get("/search/{query}")
async def search_isign_path_alias(
    query: str,
    limit: int = Query(default=10, ge=1, le=50),
) -> Dict[str, Any]:
    """Path alias for GET /api/isign/search?q=<query>."""
    return await search_isign_by_query_param(q=query, limit=limit)


@router.get("/retrieve/{uid}")
@router.post("/retrieve/{uid}")
async def retrieve_isign_pose(
    uid: str,
    force_refresh: bool = Query(default=False, description="Bypass cache if true"),
) -> Dict[str, Any]:
    """
    UID -> authentic .pose retrieval and SMPL-X conversion endpoint:
    - uses the official iSign pose archive member
    - retrieves only the required .pose member via HTTP Range request
    - does NOT download the 170 GB archive
    - verifies 116 frames, 25 FPS, 576 points, 33 body, 21 left-hand, 21 right-hand, 1 person
    - connects to SignAvatars/isign_retargeting prototype
    - produces (116, 10475, 3) float32 SMPL-X vertices
    - saves under D:\\SignAuraData\\iSign\\cache\\<uid>\\
    - saves source.pose, metadata.json, smplx.npy, pose_params.npz
    - returns cache hit immediately if already processed
    """
    clean_uid = uid.strip()
    if not clean_uid:
        raise HTTPException(status_code=400, detail="UID cannot be empty.")

    try:
        result = isign_pose_retriever.process_uid(clean_uid, force_refresh=force_refresh)
        return result
    except ISignAuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except (ISignRetrievalError, ISignIntegrityError) as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/cache/{uid}")
async def get_isign_cache_status(uid: str) -> Dict[str, Any]:
    """
    Checks cache existence and returns provenance metadata for a given UID.
    """
    clean_uid = uid.strip()
    cache_info = isign_pose_retriever.get_cache_info(clean_uid)
    if not cache_info:
        return {
            "uid": clean_uid,
            "cached": False,
            "cache_dir": str(isign_pose_retriever.cache_dir / clean_uid),
        }
    return cache_info


@router.get("/item/{uid}")
async def get_isign_item_by_uid(uid: str) -> Dict[str, Any]:
    """
    Retrieves exact iSign benchmark record by UID.
    Returns 404 if the UID is not found.
    """
    clean_uid = uid.strip()
    item = isign_metadata.get_by_uid(clean_uid)
    cached = isign_pose_retriever.is_cached(clean_uid)

    if not item:
        # Check known genuine sample registry
        lookup = isign_hf_client.lookup_by_uid(clean_uid)
        if not lookup:
            raise HTTPException(
                status_code=404,
                detail=f"iSign item with UID '{clean_uid}' not found in benchmark metadata."
            )
        return {
            "uid": lookup["uid"],
            "video_id": lookup["uid"].split("-")[0] if "-" in lookup["uid"] else lookup["uid"],
            "sequence_number": 0,
            "text": lookup["text"],
            "split": lookup.get("split", "train"),
            "source": lookup.get("source", "ISLRTC"),
            "pose_available": cached,
            "cached_in_storage": cached,
            "direct_smplx_available": cached,
            "license": "CC BY-NC-SA 4.0",
        }

    return {
        "uid": item.uid,
        "video_id": item.video_id,
        "sequence_number": item.sequence_number,
        "text": item.text,
        "split": item.split,
        "source": item.source,
        "pose_available": item.pose_available or cached,
        "video_available": item.video_available,
        "cached_in_storage": cached,
        "direct_smplx_available": cached,
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


class ISignTranslateMotionRequest(BaseModel):
    text: str = Field(..., description="English sentence/text to translate to authentic iSign motion")


@router.post("/translate-to-motion")
async def translate_text_to_isign_motion(
    req: ISignTranslateMotionRequest
) -> Dict[str, Any]:
    """
    End-to-End ISL Translation & Motion Pipeline using Authentic iSign Dataset:
    TEXT -> ISL grammar/glosses -> iSign search/UID resolution -> on-demand pose retrieval
    -> SMPL-X retargeting -> multi-sample animation sequencing.
    Returns:
    - original text
    - generated glosses
    - resolved iSign UIDs
    - unresolved glosses (if any)
    - sequence ID
    - frame count
    - FPS
    - animation / metadata URLs
    - cache information
    - clear error info when a gloss cannot be resolved.
    Zero synthetic or fake motions.
    """
    clean_text = req.text.strip()
    if not clean_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text cannot be empty."
        )

    result = isign_motion_service.translate_to_motion(clean_text)
    return result

