import datetime
import os
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

        await jobs.update_one(
            {"id": job_id},
            {
                "$set": {
                    "status": "completed",
                    "progress": 100,
                    "transcript": result["transcript"],
                    "language": result["language"],
                    "duration": result["duration"],
                    "gloss_tokens": result["tokens"],
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
        "duration": duration,
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

    job_doc = _initial_job(
        job_id=job_id,
        user_id=current_user.id,
        title=file.filename or "Uploaded Video",
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
    job_id = f"job-{uuid.uuid4().hex[:8]}"

    # IMPORTANT: actually download the media.
    # No YouTube transcript shortcut and no fake fallback.
    try:
        download_res = await video_downloader.download_media(req.url)
    except VideoDownloadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    video_path = download_res["file_path"]

    job_doc = _initial_job(
        job_id=job_id,
        user_id=current_user.id,
        title=req.title or download_res.get("title", "Web Video"),
        dialect=req.dialect or "standard",
        video_url=req.url,
        file_path=video_path,
        duration=float(download_res.get("duration") or 0.0),
    )

    job_doc["original_file_name"] = download_res.get(
        "title", "Web Video"
    )

    jobs = get_video_jobs_collection()
    await jobs.insert_one(job_doc)

    await _start_pipeline(
        background_tasks,
        video_path,
        req.dialect or "standard",
        job_id,
    )

    return VideoJobResponse(**job_doc)
