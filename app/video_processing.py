"""
Video processing module for frame extraction and video manipulation.
Supports video downloading, chunking, and frame extraction for AI analysis.
"""

import os
import logging
import subprocess
import tempfile
import shutil
import asyncio
import aiofiles
from typing import List, Dict, Any, Optional
from pathlib import Path
import cv2
import requests
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoProcessor:
    """Handles video downloading, chunking, and frame extraction."""
    
    def __init__(self, temp_dir: Optional[str] = None, frame_rate: float = 1.0, chunk_duration: int = 300):
        """
        Initialize video processor.
        
        Args:
            temp_dir: Directory for temporary files (created if None)
            frame_rate: Frame extraction rate in FPS
            chunk_duration: Duration of each chunk in seconds (default 5 minutes)
        """
        self.temp_dir = temp_dir or tempfile.mkdtemp(prefix="video_proc_")
        self.frame_rate = frame_rate
        self.chunk_duration = chunk_duration
        
        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)
        logger.info(f"VideoProcessor initialized with temp_dir: {self.temp_dir}")

    async def download_video(self, video_url: str) -> str:
        """
        Download video from URL to temporary file.
        
        Args:
            video_url: URL of the video to download
            
        Returns:
            Path to downloaded video file
        """
        logger.info(f"Downloading video from: {video_url}")
        
        # Parse URL to get filename
        parsed_url = urlparse(video_url)
        filename = os.path.basename(parsed_url.path) or "video.mp4"
        if not filename.endswith(('.mp4', '.mov', '.avi', '.mkv')):
            filename += '.mp4'
        
        video_path = os.path.join(self.temp_dir, filename)
        
        try:
            # Download with streaming to handle large files
            response = requests.get(video_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            async with aiofiles.open(video_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        await f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Log progress for large files
                        if total_size > 0 and downloaded_size % (1024 * 1024) == 0:  # Every MB
                            progress = (downloaded_size / total_size) * 100
                            logger.debug(f"Download progress: {progress:.1f}%")
            
            logger.info(f"Video downloaded successfully: {video_path} ({downloaded_size} bytes)")
            return video_path
            
        except Exception as e:
            logger.error(f"Failed to download video from {video_url}: {e}")
            raise

    def get_video_duration(self, video_path: str) -> float:
        """
        Get video duration in seconds using OpenCV.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Duration in seconds
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Could not open video: {video_path}")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            logger.info(f"Video duration: {duration:.2f} seconds ({frame_count} frames at {fps} FPS)")
            return duration
            
        except Exception as e:
            logger.error(f"Failed to get video duration for {video_path}: {e}")
            raise

    def split_video_into_chunks(self, video_path: str) -> List[str]:
        """
        Split video into chunks using FFmpeg.
        
        Args:
            video_path: Path to input video
            
        Returns:
            List of paths to chunk files
        """
        logger.info(f"Splitting video into {self.chunk_duration}s chunks: {video_path}")
        
        chunk_paths = []
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        
        try:
            # Get video duration to calculate number of chunks
            duration = self.get_video_duration(video_path)
            num_chunks = int(duration / self.chunk_duration) + (1 if duration % self.chunk_duration > 0 else 0)
            
            logger.info(f"Creating {num_chunks} chunks of {self.chunk_duration}s each")
            
            for i in range(num_chunks):
                start_time = i * self.chunk_duration
                chunk_filename = f"{base_name}_chunk_{i:03d}.mp4"
                chunk_path = os.path.join(self.temp_dir, chunk_filename)
                
                # FFmpeg command for chunk extraction
                cmd = [
                    'ffmpeg', '-y',  # -y to overwrite existing files
                    '-i', video_path,
                    '-ss', str(start_time),
                    '-t', str(self.chunk_duration),
                    '-c', 'copy',  # Copy streams without re-encoding for speed
                    '-avoid_negative_ts', 'make_zero',
                    chunk_path
                ]
                
                logger.debug(f"Running FFmpeg command: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                if result.returncode != 0:
                    logger.error(f"FFmpeg failed for chunk {i}: {result.stderr}")
                    continue
                
                if os.path.exists(chunk_path) and os.path.getsize(chunk_path) > 0:
                    chunk_paths.append(chunk_path)
                    logger.debug(f"Created chunk {i}: {chunk_path}")
                else:
                    logger.warning(f"Chunk {i} was not created or is empty")
            
            logger.info(f"Successfully created {len(chunk_paths)} video chunks")
            return chunk_paths
            
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timeout during video splitting")
            raise
        except Exception as e:
            logger.error(f"Failed to split video: {e}")
            raise

    def extract_frames_from_chunk(self, chunk_path: str, chunk_index: int, frame_rate: Optional[float] = None) -> Dict[str, Any]:
        """
        Extract frames from video chunk using OpenCV.
        
        Args:
            chunk_path: Path to video chunk
            chunk_index: Index of the chunk (for timestamp calculation)
            frame_rate: Frame extraction rate (uses instance default if None)
            
        Returns:
            Dictionary with frame_paths and timestamps
        """
        extraction_fps = frame_rate or self.frame_rate
        logger.info(f"Extracting frames from chunk {chunk_index} at {extraction_fps} FPS: {chunk_path}")
        
        try:
            cap = cv2.VideoCapture(chunk_path)
            if not cap.isOpened():
                raise ValueError(f"Could not open chunk: {chunk_path}")
            
            # Get video properties
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if video_fps <= 0:
                logger.warning(f"Invalid FPS {video_fps}, using default 30")
                video_fps = 30
            
            # Calculate frame interval for extraction
            frame_interval = max(1, int(video_fps / extraction_fps))
            
            frame_paths = []
            timestamps = []
            chunk_start_time = chunk_index * self.chunk_duration
            
            frame_number = 0
            extracted_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Extract frame at specified intervals
                if frame_number % frame_interval == 0:
                    # Calculate timestamp
                    timestamp = chunk_start_time + (frame_number / video_fps)
                    
                    # Save frame
                    frame_filename = f"chunk_{chunk_index:03d}_frame_{extracted_count:06d}.jpg"
                    frame_path = os.path.join(self.temp_dir, frame_filename)
                    
                    # Save with high quality
                    success = cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                    
                    if success:
                        frame_paths.append(frame_path)
                        timestamps.append(timestamp)
                        extracted_count += 1
                        logger.debug(f"Extracted frame {extracted_count} at {timestamp:.2f}s")
                    else:
                        logger.warning(f"Failed to save frame at {timestamp:.2f}s")
                
                frame_number += 1
            
            cap.release()
            
            logger.info(f"Extracted {len(frame_paths)} frames from chunk {chunk_index}")
            
            return {
                'frame_paths': frame_paths,
                'timestamps': timestamps,
                'chunk_index': chunk_index,
                'total_extracted': len(frame_paths)
            }
            
        except Exception as e:
            logger.error(f"Failed to extract frames from chunk {chunk_index}: {e}")
            raise

    def cleanup(self):
        """Clean up temporary directory and all files."""
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                logger.error(f"Failed to cleanup temp directory {self.temp_dir}: {e}")

    def __del__(self):
        """Ensure cleanup on object destruction."""
        self.cleanup() 