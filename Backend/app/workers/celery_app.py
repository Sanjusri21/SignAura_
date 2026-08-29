import asyncio
import logging
from typing import Optional

from celery import Celery

from app.core.config import settings
from app.core.database import get_video_jobs_collection
from app.services.video.ffmpeg_processor import ffmpeg_processor
from app.services.speech.whisper_service import whisper_service
from app.services.nlp.tokenizer import nlp_processor
from app.services.isl.service import get_isl_service

logger = logging.getLogger("signaura.celery")

celery_app = Celery(
    "signaura_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)


async def execute_video_pipeline(
    video_path: str,
    dialect: str = "standard",
    job_id: str = "job-default",
    transcript_override: Optional[str] = None,
):
    """Real media -> FFmpeg -> Whisper -> NLP -> ISL pipeline."""

    logger.info("Starting pipeline job=%s path=%s", job_id, video_path)

    # text_override is retained ONLY for explicit API testing.
    # The YouTube URL pipeline passes None.
    if transcript_override and transcript_override.strip():
        text = transcript_override.strip()
        language = "en"
        duration = 0.0
        segments = []
    else:
        if not video_path:
            raise RuntimeError("No downloaded media file was provided.")

        audio_path = await ffmpeg_processor.extract_audio(video_path)

        transcription = await whisper_service.transcribe(
            audio_path,
            language=None,  # auto-detect actual spoken language
        )
        text = transcription["text"]
        language = transcription.get("language", "unknown")
        duration = float(transcription.get("duration") or 0.0)
        segments = transcription.get("segments") or []

    if not text.strip():
        raise RuntimeError("No speech was detected in the media.")

    logger.info("Job %s transcript: %s", job_id, text)

    nlp_tokens = nlp_processor.analyze_text(text)

    isl_service = get_isl_service()
    isl_result = await isl_service.translate_to_gloss(
        text, dialect=dialect
    )

    return {
        "job_id": job_id,
        "status": "completed",
        "transcript": text,
        "language": language,
        "duration": duration,
        "segments": segments,
        "nlp_tokens": nlp_tokens,
        "gloss": isl_result.gloss,
        "animations": isl_result.animations,
        "tokens": [
            t.model_dump() if hasattr(t, "model_dump") else t.dict()
            for t in (isl_result.tokens or [])
        ],
    }


async def _update_job(job_id: str, values: dict):
    jobs = get_video_jobs_collection()
    await jobs.update_one({"id": job_id}, {"$set": values})


async def _run_task_and_update(
    video_path: str, dialect: str, job_id: str
):
    try:
        await _update_job(
            job_id,
            {"status": "processing", "progress": 40},
        )

        result = await execute_video_pipeline(
            video_path, dialect=dialect, job_id=job_id
        )

        await _update_job(
            job_id,
            {
                "status": "completed",
                "progress": 100,
                "transcript": result["transcript"],
                "language": result["language"],
                "duration": result["duration"],
                "gloss_tokens": result["tokens"],
                "accuracy": 0.0,
                "updated_at": __import__("datetime").datetime.utcnow().isoformat(),
            },
        )
        return result
    except Exception as exc:
        logger.exception("Job %s failed", job_id)
        await _update_job(
            job_id,
            {
                "status": "failed",
                "progress": 100,
                "error": str(exc),
                "updated_at": __import__("datetime").datetime.utcnow().isoformat(),
            },
        )
        raise


@celery_app.task(name="process_video_pipeline_task")
def process_video_pipeline_task(
    video_path: str,
    dialect: str = "standard",
    job_id: str = "job-default",
):
    return asyncio.run(_run_task_and_update(video_path, dialect, job_id))
