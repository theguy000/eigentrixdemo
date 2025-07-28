"""
Job Manager for async video annotation processing.
Handles background processing and job status tracking.
"""

import asyncio
import threading
import time
import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobResult:
    """Container for job results and metadata."""
    
    def __init__(self, job_id: str, video_url: str, frame_rate: float):
        self.job_id = job_id
        self.video_url = video_url
        self.frame_rate = frame_rate
        self.status = JobStatus.PENDING
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.progress: Dict[str, Any] = {}
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.processing_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job result to dictionary for API response."""
        base_dict = {
            "job_id": self.job_id,
            "status": self.status.value,
            "video_url": self.video_url,
            "frame_rate": self.frame_rate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "processing_time": self.processing_time,
            "progress": self.progress
        }
        
        if self.status == JobStatus.COMPLETED and self.result:
            base_dict.update(self.result)
        elif self.status == JobStatus.FAILED and self.error:
            base_dict["error"] = self.error
            
        return base_dict

class JobManager:
    """Manages background video annotation jobs."""
    
    def __init__(self):
        self.jobs: Dict[str, JobResult] = {}
        self.cleanup_interval = 3600  # 1 hour
        self.max_job_age = 24 * 3600  # 24 hours
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False
        logger.info("JobManager initialized")

    def start(self):
        """Start the job manager and cleanup thread."""
        if self._running:
            return
            
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        logger.info("JobManager started")

    def stop(self):
        """Stop the job manager."""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        logger.info("JobManager stopped")

    def create_job(self, video_url: str, frame_rate: float = 1.0) -> str:
        """Create a new annotation job and return job ID."""
        job_id = str(uuid.uuid4())
        job_result = JobResult(job_id, video_url, frame_rate)
        self.jobs[job_id] = job_result
        
        logger.info(f"Created job {job_id} for video: {video_url}")
        return job_id

    def get_job(self, job_id: str) -> Optional[JobResult]:
        """Get job result by ID."""
        return self.jobs.get(job_id)

    def update_job_status(self, job_id: str, status: JobStatus, **kwargs):
        """Update job status and metadata."""
        if job_id not in self.jobs:
            logger.warning(f"Attempted to update non-existent job: {job_id}")
            return
            
        job = self.jobs[job_id]
        job.status = status
        
        if status == JobStatus.PROCESSING and not job.started_at:
            job.started_at = datetime.utcnow()
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            job.completed_at = datetime.utcnow()
            if job.started_at:
                job.processing_time = (job.completed_at - job.started_at).total_seconds()
        
        # Update additional fields
        for key, value in kwargs.items():
            setattr(job, key, value)
            
        logger.debug(f"Updated job {job_id} status to {status.value}")

    def update_job_progress(self, job_id: str, progress: Dict[str, Any]):
        """Update job progress information."""
        if job_id not in self.jobs:
            return
            
        self.jobs[job_id].progress.update(progress)
        logger.debug(f"Updated job {job_id} progress: {progress}")

    def set_job_result(self, job_id: str, result: Dict[str, Any]):
        """Set the final result for a completed job."""
        if job_id not in self.jobs:
            logger.warning(f"Attempted to set result for non-existent job: {job_id}")
            return
            
        self.jobs[job_id].result = result
        self.update_job_status(job_id, JobStatus.COMPLETED)
        logger.info(f"Job {job_id} completed successfully with {len(result.get('annotations', []))} annotations")

    def set_job_error(self, job_id: str, error: str):
        """Set error for a failed job."""
        if job_id not in self.jobs:
            logger.warning(f"Attempted to set error for non-existent job: {job_id}")
            return
            
        self.jobs[job_id].error = error
        self.update_job_status(job_id, JobStatus.FAILED)
        logger.error(f"Job {job_id} failed: {error}")

    def list_jobs(self, limit: int = 100) -> Dict[str, Any]:
        """List recent jobs."""
        jobs_list = sorted(
            self.jobs.values(), 
            key=lambda x: x.created_at, 
            reverse=True
        )[:limit]
        
        return {
            "jobs": [job.to_dict() for job in jobs_list],
            "total": len(self.jobs),
            "active": len([j for j in self.jobs.values() if j.status in [JobStatus.PENDING, JobStatus.PROCESSING]])
        }

    def cleanup_old_jobs(self):
        """Remove old completed jobs to prevent memory leaks."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.max_job_age)
        old_jobs = [
            job_id for job_id, job in self.jobs.items()
            if job.created_at < cutoff_time and job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
        ]
        
        for job_id in old_jobs:
            del self.jobs[job_id]
            
        if old_jobs:
            logger.info(f"Cleaned up {len(old_jobs)} old jobs")

    def _cleanup_worker(self):
        """Background worker for periodic cleanup."""
        while self._running:
            try:
                self.cleanup_old_jobs()
                time.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
                time.sleep(60)  # Wait a minute before retrying

    def get_stats(self) -> Dict[str, Any]:
        """Get job manager statistics."""
        status_counts = {}
        for status in JobStatus:
            status_counts[status.value] = len([
                j for j in self.jobs.values() if j.status == status
            ])
            
        return {
            "total_jobs": len(self.jobs),
            "status_breakdown": status_counts,
            "oldest_job": min([j.created_at for j in self.jobs.values()]).isoformat() if self.jobs else None,
            "newest_job": max([j.created_at for j in self.jobs.values()]).isoformat() if self.jobs else None
        }

# Global job manager instance
job_manager = JobManager() 