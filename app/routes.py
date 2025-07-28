"""
FastAPI routes for async video annotation with Gemini Pro Vision integration.
Phase 3: Async job system - returns job_id immediately, processes in background.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
import os
import tempfile
import shutil

from .job_manager import job_manager, JobStatus
from .background_worker import background_worker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class VideoAnnotationRequest(BaseModel):
    """Request model for video annotation."""
    video_url: HttpUrl
    frame_rate: float = 1.0  # frames per second for extraction

class JobResponse(BaseModel):
    """Response model for job creation."""
    job_id: str
    status: str
    message: str
    video_url: str
    frame_rate: float
    created_at: str

class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: str
    status: str
    video_url: str
    frame_rate: float
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    processing_time: Optional[float] = None
    progress: Dict[str, Any] = {}
    # When completed, include all annotation results
    duration_seconds: Optional[float] = None
    total_frames_processed: Optional[int] = None
    annotations: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

@router.post("/api/annotate", response_model=JobResponse)
async def create_annotation_job(request: VideoAnnotationRequest) -> JobResponse:
    """
    Create an async video annotation job.
    
    Returns job_id immediately and starts processing in background.
    Use GET /api/status/{job_id} to check progress and get results.
    """
    try:
        logger.info(f"Creating annotation job for: {request.video_url}")
        
        # Create job and get job_id
        job_id = job_manager.create_job(
            video_url=str(request.video_url),
            frame_rate=request.frame_rate
        )
        
        # Get job details for response
        job = job_manager.get_job(job_id)
        
        logger.info(f"Created job {job_id}, processing will start shortly")
        
        return JobResponse(
            job_id=job_id,
            status=job.status.value,
            message="Job created successfully. Processing will begin shortly.",
            video_url=str(request.video_url),
            frame_rate=request.frame_rate,
            created_at=job.created_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to create annotation job: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create annotation job: {str(e)}"
        )

@router.get("/api/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """
    Get the status and results of an annotation job.
    
    Returns current status, progress, and results if completed.
    """
    try:
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        job_dict = job.to_dict()
        
        logger.debug(f"Status request for job {job_id}: {job.status.value}")
        
        return JobStatusResponse(**job_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job status: {str(e)}"
        )

@router.delete("/api/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a pending or processing job."""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job in {job.status.value} status"
            )
        
        job_manager.update_job_status(job_id, JobStatus.CANCELLED)
        logger.info(f"Cancelled job {job_id}")
        
        return {
            "job_id": job_id,
            "status": "cancelled",
            "message": "Job cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel job: {str(e)}"
        )

@router.get("/api/jobs")
async def list_jobs(limit: int = 50):
    """List recent annotation jobs."""
    try:
        jobs_info = job_manager.list_jobs(limit=limit)
        logger.debug(f"Listed {len(jobs_info['jobs'])} jobs")
        return jobs_info
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list jobs: {str(e)}"
        )

@router.get("/api/jobs/stats")
async def get_job_stats():
    """Get job processing statistics."""
    try:
        stats = job_manager.get_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get job stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job stats: {str(e)}"
        )

@router.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        stats = job_manager.get_stats()
        worker_status = "running" if background_worker.running else "stopped"
        
        return {
            "status": "healthy",
            "service": "video-annotation-api",
            "version": "3.0.0",
            "features": "async-job-processing",
            "background_worker": worker_status,
            "active_jobs": stats["status_breakdown"].get("processing", 0),
            "pending_jobs": stats["status_breakdown"].get("pending", 0)
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# Legacy endpoint for backward compatibility (now returns job_id)
@router.post("/api/annotate/sync")
async def annotate_video_sync(request: VideoAnnotationRequest):
    """
    Legacy synchronous endpoint for backward compatibility.
    
    Creates a job but waits for completion before returning results.
    Use /api/annotate for async processing instead.
    """
    logger.warning("Using deprecated sync endpoint - consider switching to async /api/annotate")
    
    # Create job
    job_response = await create_annotation_job(request)
    job_id = job_response.job_id
    
    # Wait for completion (with timeout)
    timeout = 1800  # 30 minutes max
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        job = job_manager.get_job(job_id)
        
        if job.status == JobStatus.COMPLETED:
            return job.result
        elif job.status == JobStatus.FAILED:
            raise HTTPException(
                status_code=500,
                detail=f"Job failed: {job.error}"
            )
        
        # Wait before checking again
        await asyncio.sleep(5)
    
    # Timeout
    raise HTTPException(
        status_code=408,
        detail=f"Job {job_id} timed out after {timeout} seconds"
    ) 