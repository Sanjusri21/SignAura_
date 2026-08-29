from fastapi import APIRouter, HTTPException, status
from app.schemas.job import JobStatusResponse
from app.core.database import get_video_jobs_collection

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    jobs = get_video_jobs_collection()
    job_doc = await jobs.find_one({"id": job_id})
    if not job_doc:
        job_doc = await jobs.find_one({"job_id": job_id})
        
    if not job_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
        
    return JobStatusResponse(**job_doc)
