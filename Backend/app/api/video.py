import datetime
import os
import re
import uuid
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from app.api.auth import get_current_user
from app.core.config import settings
from app.core.database import get_video_jobs_collection
from app.schemas.auth import UserResponse
from app.schemas.video import VideoJobResponse, VideoProcessUrlRequest
from app.services.video.downloader import VideoDownloadError, video_downloader
from app.workers.celery_app import (
    execute_video_pipeline,
    process_video_pipeline_task,
)

router = APIRouter(prefix="/video", tags=["Video Processing"])


async def run_pipeline_in_background(
    file_path: str,
    dialect: str,
    job_id: str,
):
    """Local fallback runner when Celery is disabled/unavailable."""
    jobs = get_video_jobs_collection()

    try:
        await jobs.update_one(
            {"id": job_id},
            {"$set": {"status": "processing", "progress": 40}},
        )

        result = await execute_video_pipeline(
            file_path, dialect=dialect, job_id=job_id
        )

        existing_doc = await jobs.find_one({"id": job_id})
        current_title = (existing_doc or {}).get("title", "")
        # If title is generic, derive meaningful title from first words of transcript
        if not current_title or current_title in ("Web Video Conversion", "Web Video Processing", "Web Stream Video", "Online Video Stream"):
            transcript_words = result.get("transcript", "").strip().split()[:7]
            if transcript_words:
                current_title = " ".join(transcript_words) + "..."
            else:
                current_title = "Audio Conversion"

        await jobs.update_one(
            {"id": job_id},
            {
                "$set": {
                    "title": current_title,
                    "status": "completed",
                    "progress": 100,
                    "transcript": result["transcript"],
                    "language": result["language"],
                    "duration": round(float(result["duration"]), 1),
                    "gloss_tokens": result["tokens"],
                    "language_supported": result.get("language_supported", True),
                    "message": result.get("message"),
                    "accuracy": 0.0,
                    "updated_at": datetime.datetime.utcnow().isoformat(),
                }
            },
        )
    except Exception as exc:
        await jobs.update_one(
            {"id": job_id},
            {
                "$set": {
                    "status": "failed",
                    "progress": 100,
                    "error": str(exc),
                    "updated_at": datetime.datetime.utcnow().isoformat(),
                }
            },
        )


def _initial_job(
    job_id: str,
    user_id: str,
    title: str,
    dialect: str,
    video_url: Optional[str] = None,
    file_path: Optional[str] = None,
    duration: float = 0.0,
    language: str = "unknown",
):
    return {
        "id": job_id,
        "job_id": job_id,
        "user_id": user_id,
        "title": title,
        "original_file_name": title,
        "video_url": video_url,
        "file_path": file_path,
        "status": "processing",
        "progress": 30,
        "duration": round(float(duration or 0.0), 1),
        "accuracy": 0.0,
        "language": language,
        "dialect": dialect,
        "transcript": "",
        "gloss_tokens": [],
        "created_at": datetime.datetime.utcnow().isoformat(),
    }


async def _start_pipeline(
    background_tasks: BackgroundTasks,
    file_path: str,
    dialect: str,
    job_id: str,
):
    if not file_path:
        raise HTTPException(
            status_code=500,
            detail="No media file was downloaded.",
        )

    if settings.ENABLE_CELERY:
        try:
            process_video_pipeline_task.delay(
                file_path, dialect, job_id
            )
            return
        except Exception:
            # If Redis/Celery is unavailable, use FastAPI BackgroundTasks.
            pass

    background_tasks.add_task(
        run_pipeline_in_background,
        file_path,
        dialect,
        job_id,
    )


@router.post("/upload", response_model=VideoJobResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    dialect: str = Form("standard"),
    current_user: UserResponse = Depends(get_current_user),
):
    job_id = f"job-{uuid.uuid4().hex[:8]}"
    file_ext = os.path.splitext(file.filename or "")[1] or ".mp4"
    save_path = os.path.join(
        settings.UPLOADS_DIR, f"{job_id}{file_ext}"
    )

    content = await file.read()
    if not content:
        raise HTTPException(400, "Uploaded video is empty.")

    with open(save_path, "wb") as f:
        f.write(content)

    clean_filename = os.path.splitext(file.filename or "")[0] or "Uploaded Video"
    clean_title = re.sub(r"[_-]+", " ", clean_filename).strip() or "Uploaded Video"

    job_doc = _initial_job(
        job_id=job_id,
        user_id=current_user.id,
        title=clean_title,
        dialect=dialect,
        file_path=save_path,
    )

    jobs = get_video_jobs_collection()
    await jobs.insert_one(job_doc)
    await _start_pipeline(
        background_tasks, save_path, dialect, job_id
    )

    return VideoJobResponse(**job_doc)


@router.post("/process-url", response_model=VideoJobResponse)
async def process_video_url(
    req: VideoProcessUrlRequest,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user),
):
    jobs = get_video_jobs_collection()

    # Prevent duplicate conversions: check if identical URL was already completed for user
    if not getattr(req, "force_reconvert", False):
        existing = await jobs.find_one({
            "user_id": current_user.id,
            "video_url": req.url,
            "status": "completed",
        })
        if existing:
            return VideoJobResponse(
                job_id=existing.get("job_id", existing.get("id")),
                title=existing.get("title", "Existing Video"),
                status="completed",
                video_url=existing.get("video_url"),
                original_file_name=existing.get("original_file_name"),
                created_at=str(existing.get("created_at", "")),
                progress=100,
                duration=round(float(existing.get("duration", 0.0) or 0.0), 1),
                accuracy=existing.get("accuracy", 0.0),
                language=existing.get("language", "en"),
                dialect=existing.get("dialect", "standard"),
                transcript=existing.get("transcript", ""),
                gloss_tokens=existing.get("gloss_tokens", []),
                language_supported=existing.get("language_supported", True),
                message=existing.get("message"),
                is_existing=True,
            )

    job_id = f"job-{uuid.uuid4().hex[:8]}"

    # IMPORTANT: actually download the media via yt-dlp
    try:
        download_res = await video_downloader.download_media(req.url)
    except VideoDownloadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    video_path = download_res["file_path"]

    # Meaningful title extraction: prioritize real video title
    extracted_title = download_res.get("title") or req.title or "Online Video"
    extracted_title = re.sub(r"YouTube Video \([^\)]+\)", "", extracted_title).strip()
    if not extracted_title or extracted_title == "Online Video":
        extracted_title = "Online Video Lecture"

    job_doc = _initial_job(
        job_id=job_id,
        user_id=current_user.id,
        title=extracted_title,
        dialect=req.dialect or "standard",
        video_url=req.url,
        file_path=video_path,
        duration=round(float(download_res.get("duration") or 0.0), 1),
    )

    job_doc["original_file_name"] = download_res.get(
        "title", extracted_title
    )

    await jobs.insert_one(job_doc)

    await _start_pipeline(
        background_tasks,
        video_path,
        req.dialect or "standard",
        job_id,
    )

    return VideoJobResponse(**job_doc)

