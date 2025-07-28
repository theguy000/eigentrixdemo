"""
Background worker for processing video annotation jobs.
Handles the actual video processing without blocking the API.
"""

import asyncio
import threading
import time
import logging
import tempfile
import shutil
import os
from typing import Dict, Any

from .job_manager import job_manager, JobStatus
from .video_processing import VideoProcessor
from services.gemini import GeminiAnalyzer

logger = logging.getLogger(__name__)

class BackgroundWorker:
    """Background worker for processing annotation jobs."""
    
    def __init__(self, max_concurrent_jobs: int = 2):
        self.max_concurrent_jobs = max_concurrent_jobs
        self.worker_threads = []
        self.running = False
        self._stop_event = threading.Event()
        logger.info(f"BackgroundWorker initialized with {max_concurrent_jobs} max concurrent jobs")

    def start(self):
        """Start the background worker threads."""
        if self.running:
            return
            
        self.running = True
        self._stop_event.clear()
        
        # Start worker threads
        for i in range(self.max_concurrent_jobs):
            thread = threading.Thread(
                target=self._worker_loop,
                name=f"AnnotationWorker-{i}",
                daemon=True
            )
            thread.start()
            self.worker_threads.append(thread)
            
        logger.info(f"Started {len(self.worker_threads)} background worker threads")

    def stop(self):
        """Stop the background worker."""
        if not self.running:
            return
            
        self.running = False
        self._stop_event.set()
        
        # Wait for threads to finish
        for thread in self.worker_threads:
            thread.join(timeout=10)
            
        self.worker_threads.clear()
        logger.info("Background worker stopped")

    def _worker_loop(self):
        """Main worker loop that processes pending jobs."""
        logger.info(f"Worker thread {threading.current_thread().name} started")
        
        while self.running and not self._stop_event.is_set():
            try:
                # Look for pending jobs
                pending_job = self._find_pending_job()
                
                if pending_job:
                    self._process_job(pending_job.job_id)
                else:
                    # No pending jobs, wait a bit
                    time.sleep(2)
                    
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                time.sleep(5)  # Wait before retrying
                
        logger.info(f"Worker thread {threading.current_thread().name} stopped")

    def _find_pending_job(self):
        """Find the next pending job to process."""
        for job in job_manager.jobs.values():
            if job.status == JobStatus.PENDING:
                return job
        return None

    def _run_async_in_thread(self, coro):
        """Run an async coroutine in a thread-safe way."""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error running async function: {e}")
            raise

    def _process_job(self, job_id: str):
        """Process a single annotation job."""
        job = job_manager.get_job(job_id)
        if not job:
            logger.warning(f"Job {job_id} not found during processing")
            return

        logger.info(f"Starting processing for job {job_id}: {job.video_url}")
        
        # Mark job as processing
        job_manager.update_job_status(job_id, JobStatus.PROCESSING)
        temp_dir = None
        
        try:
            # Create temporary directory for processing
            temp_dir = tempfile.mkdtemp(prefix="video_annotation_")
            
            # Initialize video processor
            processor = VideoProcessor(
                temp_dir=temp_dir,
                frame_rate=job.frame_rate,
                chunk_duration=300  # 5 minutes
            )
            
            # Update progress: Starting download
            job_manager.update_job_progress(job_id, {
                "stage": "downloading",
                "message": "Downloading video from URL"
            })
            
            # Download and process video
            video_path = self._run_async_in_thread(
                processor.download_video(job.video_url)
            )
            
            # Update progress: Getting video info
            job_manager.update_job_progress(job_id, {
                "stage": "analyzing",
                "message": "Extracting video information"
            })
            
            duration = processor.get_video_duration(video_path)
            
            # Update progress: Splitting video
            job_manager.update_job_progress(job_id, {
                "stage": "splitting",
                "message": "Splitting video into chunks",
                "duration_seconds": duration
            })
            
            chunk_paths = processor.split_video_into_chunks(video_path)
            
            # Process each chunk
            all_annotations = []
            total_frames = 0
            
            for i, chunk_path in enumerate(chunk_paths):
                # Update progress: Processing chunk
                job_manager.update_job_progress(job_id, {
                    "stage": "processing_chunks",
                    "message": f"Processing chunk {i+1} of {len(chunk_paths)}",
                    "current_chunk": i + 1,
                    "total_chunks": len(chunk_paths),
                    "progress_percent": int((i / len(chunk_paths)) * 100)
                })
                
                try:
                    # Extract frames from chunk
                    frame_info = processor.extract_frames_from_chunk(
                        chunk_path, 
                        chunk_index=i,
                        frame_rate=job.frame_rate
                    )
                    
                    frame_paths = frame_info['frame_paths']
                    frame_timestamps = frame_info['timestamps']
                    total_frames += len(frame_paths)
                    
                    if frame_paths:
                        # Update progress: AI analysis
                        job_manager.update_job_progress(job_id, {
                            "stage": "ai_analysis",
                            "message": f"Running AI analysis on {len(frame_paths)} frames",
                            "current_chunk": i + 1,
                            "frames_in_chunk": len(frame_paths)
                        })
                        
                        # Analyze frames with Gemini API - pass frame rate for optimization
                        gemini_analyzer = GeminiAnalyzer(frame_rate=job.frame_rate)
                        chunk_annotations = self._run_async_in_thread(
                            gemini_analyzer.analyze_frames(frame_paths, frame_timestamps)
                        )
                        
                        all_annotations.extend(chunk_annotations)
                    
                    # Cleanup chunk file
                    try:
                        os.unlink(chunk_path)
                    except:
                        pass
                        
                except Exception as e:
                    logger.error(f"Failed to process chunk {i+1} for job {job_id}: {e}")
                    continue
            
            # Update progress: Finalizing
            job_manager.update_job_progress(job_id, {
                "stage": "finalizing",
                "message": "Finalizing results",
                "progress_percent": 100
            })
            
            # Prepare final result in same format as Phase 2
            result = {
                "status": "completed",
                "video_url": job.video_url,
                "duration_seconds": duration,
                "total_frames_processed": total_frames,
                "annotations": all_annotations
            }
            
            # Set job result
            job_manager.set_job_result(job_id, result)
            
            logger.info(f"Job {job_id} completed successfully: {len(all_annotations)} annotations from {total_frames} frames")
            
        except Exception as e:
            error_msg = f"Job processing failed: {str(e)}"
            logger.error(f"Job {job_id} failed: {error_msg}")
            job_manager.set_job_error(job_id, error_msg)
            
        finally:
            # Cleanup temporary directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")

# Global background worker instance
background_worker = BackgroundWorker(max_concurrent_jobs=2) 