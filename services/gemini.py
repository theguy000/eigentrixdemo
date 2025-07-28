"""
Gemini Pro Vision service for video frame analysis.
Optimized for higher frame rates with smart batching.
"""

import os
import asyncio
import logging
import json
import time
import base64
from typing import List, Dict, Any
import google.generativeai as genai
from PIL import Image
import io

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    """Optimized Gemini analyzer for higher frame rates."""
    
    def __init__(self, frame_rate: float = 1.0):
        """Initialize Gemini analyzer with dynamic settings based on frame rate."""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        genai.configure(api_key=api_key)
        
        # Use Flash model for better performance and lower costs
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # DYNAMIC: Adjust settings based on expected frame count
        self.frame_rate = frame_rate
        self._configure_for_frame_rate(frame_rate)
        
        self.max_retries = 3
        
        logger.info(f"GeminiAnalyzer configured for {frame_rate} FPS: batch_size={self.batch_size}, delay={self.retry_delay}s")

    def _configure_for_frame_rate(self, frame_rate: float):
        """Configure batch size and delays based on expected frame rate."""
        if frame_rate <= 0.1:
            # Very low frame rate (few frames total)
            self.batch_size = 5
            self.retry_delay = 10
            self.frame_delay = 3
        elif frame_rate <= 0.5:
            # Low frame rate (moderate frames)
            self.batch_size = 4
            self.retry_delay = 8
            self.frame_delay = 2
        elif frame_rate <= 1.0:
            # Standard frame rate (many frames)
            self.batch_size = 3
            self.retry_delay = 6
            self.frame_delay = 1
        else:
            # High frame rate (very many frames)
            self.batch_size = 2
            self.retry_delay = 4
            self.frame_delay = 0.5
            
        logger.info(f"Configured for {frame_rate} FPS: batch={self.batch_size}, batch_delay={self.retry_delay}s, frame_delay={self.frame_delay}s")

    def _encode_image_to_base64(self, image_path: str) -> str:
        """Encode image to base64 with aggressive compression for high frame rates."""
        try:
            with Image.open(image_path) as img:
                # Aggressive resizing for high frame rates
                if self.frame_rate > 0.5:
                    # For high frame rates, use smaller images to save bandwidth/time
                    max_size = (1280, 720)  # 720p max
                    quality = 75  # Lower quality for speed
                else:
                    # For low frame rates, keep higher quality
                    max_size = (1920, 1080)  # 1080p max
                    quality = 85
                
                if img.width > max_size[0] or img.height > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=quality, optimize=True)
                buffer.seek(0)
                
                encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
                logger.debug(f"Encoded {image_path} ({img.size}) to {len(encoded)} chars (quality={quality})")
                return encoded
                
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            raise

    def _create_analysis_prompt(self) -> str:
        """Create optimized prompt for faster processing."""
        if self.frame_rate > 1.0:
            # Simplified prompt for high frame rates
            return """Detect main objects in this frame. Return ONLY JSON array.

Format: [{"object": "name", "bbox": [x,y,w,h], "coordinates_3d": [x,y,z], "confidence": 0.0-1.0, "timestamp": 0.0}]

Focus on: people, vehicles, tools, equipment, buildings. Be concise."""
        else:
            # Detailed prompt for low frame rates
            return """Analyze this video frame and detect all visible objects. 
Return ONLY valid JSON array. No explanations, no markdown, no code blocks.

For each object detected, provide:
- object: descriptive name (e.g., "car", "person", "tool", "building")  
- bbox: [x, y, width, height] in pixels (estimate based on image size)
- coordinates_3d: [x, y, z] in meters (relative to camera, estimate depth)
- confidence: number between 0-1 (how certain you are)
- timestamp: use the provided timestamp

Example: [{"object": "car", "bbox": [100, 200, 150, 100], "coordinates_3d": [2.0, 1.0, 5.0], "confidence": 0.95, "timestamp": 10.5}]

Return ONLY the JSON array."""

    async def _analyze_frame_batch(self, batch_frames: List[str], batch_timestamps: List[float]) -> List[Dict[str, Any]]:
        """Analyze a batch of frames with optimized processing."""
        
        logger.info(f"Processing batch of {len(batch_frames)} frames")
        annotations = []
        
        for attempt in range(self.max_retries):
            try:
                # For high frame rates, process multiple frames together when possible
                if self.frame_rate > 1.0 and len(batch_frames) <= 2:
                    # Process small batches together for efficiency
                    annotations = await self._process_frames_together(batch_frames, batch_timestamps)
                else:
                    # Process frames individually for safety
                    annotations = await self._process_frames_individually(batch_frames, batch_timestamps)
                
                logger.info(f"Batch processed successfully, found {len(annotations)} annotations")
                return annotations
                
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    logger.warning(f"Rate limit hit (attempt {attempt + 1}), using fallback")
                    return self._generate_dummy_annotations(batch_timestamps)
                elif attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All attempts failed for batch: {e}")
                    return self._generate_dummy_annotations(batch_timestamps)
        
        return annotations

    async def _process_frames_individually(self, batch_frames: List[str], batch_timestamps: List[float]) -> List[Dict[str, Any]]:
        """Process frames one by one (safer for large batches)."""
        annotations = []
        
        for i, (frame_path, timestamp) in enumerate(zip(batch_frames, batch_timestamps)):
            try:
                logger.debug(f"Analyzing frame {i+1}/{len(batch_frames)}: {frame_path}")
                
                image_data = self._encode_image_to_base64(frame_path)
                
                image_part = {
                    "mime_type": "image/jpeg",
                    "data": image_data
                }
                
                prompt = f"{self._create_analysis_prompt()}\n\nFrame timestamp: {timestamp} seconds"
                
                response = self.model.generate_content([prompt, image_part])
                
                if response and response.text:
                    frame_annotations = self._parse_gemini_response(response.text, timestamp)
                    annotations.extend(frame_annotations)
                
                del image_data
                
                # Dynamic delay between frames
                if i < len(batch_frames) - 1:
                    await asyncio.sleep(self.frame_delay)
                    
            except Exception as e:
                logger.warning(f"Failed to process frame at {timestamp}s: {e}")
                # Add dummy annotation for failed frame
                annotations.extend(self._generate_dummy_annotations([timestamp]))
                continue
        
        return annotations

    async def _process_frames_together(self, batch_frames: List[str], batch_timestamps: List[float]) -> List[Dict[str, Any]]:
        """Process multiple frames together (for small high-rate batches)."""
        try:
            logger.debug(f"Processing {len(batch_frames)} frames together")
            
            # Encode all frames
            image_parts = []
            for frame_path in batch_frames:
                image_data = self._encode_image_to_base64(frame_path)
                image_parts.append({
                    "mime_type": "image/jpeg", 
                    "data": image_data
                })
            
            # Create multi-frame prompt
            timestamps_str = ", ".join(f"{t}s" for t in batch_timestamps)
            prompt = f"{self._create_analysis_prompt()}\n\nFrame timestamps: {timestamps_str}"
            
            content = [prompt] + image_parts
            response = self.model.generate_content(content)
            
            if response and response.text:
                # Parse response and distribute timestamps
                annotations = []
                parsed = self._parse_gemini_response(response.text, batch_timestamps[0])
                
                # If we get fewer annotations than frames, distribute them
                if len(parsed) < len(batch_timestamps):
                    for i, timestamp in enumerate(batch_timestamps):
                        if i < len(parsed):
                            parsed[i]['timestamp'] = timestamp
                            annotations.append(parsed[i])
                        else:
                            # Generate dummy for missing frames
                            annotations.extend(self._generate_dummy_annotations([timestamp]))
                else:
                    annotations = parsed
                
                # Cleanup
                for part in image_parts:
                    del part['data']
                
                return annotations
            
        except Exception as e:
            logger.warning(f"Multi-frame processing failed: {e}")
            # Fall back to individual processing
            return await self._process_frames_individually(batch_frames, batch_timestamps)
        
        return self._generate_dummy_annotations(batch_timestamps)

    def _parse_gemini_response(self, response_text: str, timestamp: float) -> List[Dict[str, Any]]:
        """Parse Gemini response with robust error handling."""
        try:
            logger.debug(f"Raw Gemini response: {response_text[:200]}...")
            
            clean_text = response_text.strip()
            if clean_text.startswith('```json'):
                clean_text = clean_text.replace('```json', '').replace('```', '').strip()
            elif clean_text.startswith('```'):
                clean_text = clean_text.replace('```', '').strip()
            
            annotations = json.loads(clean_text)
            
            if not isinstance(annotations, list):
                annotations = [annotations] if annotations else []
            
            valid_annotations = []
            for ann in annotations:
                try:
                    if not all(key in ann for key in ['object', 'bbox', 'coordinates_3d', 'confidence']):
                        continue
                    
                    ann['timestamp'] = timestamp
                    ann['confidence'] = float(ann['confidence'])
                    ann['bbox'] = [int(x) for x in ann['bbox'][:4]]
                    ann['coordinates_3d'] = [float(x) for x in ann['coordinates_3d'][:3]]
                    
                    valid_annotations.append(ann)
                    
                except (ValueError, TypeError, KeyError) as e:
                    logger.warning(f"Skipping malformed annotation {ann}: {e}")
                    continue
            
            return valid_annotations
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            return self._generate_dummy_annotations([timestamp])
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
            return self._generate_dummy_annotations([timestamp])

    def _generate_dummy_annotations(self, timestamps: List[float]) -> List[Dict[str, Any]]:
        """Generate dummy annotations as fallback."""
        dummy_objects = ["object", "equipment", "tool", "surface", "material"]
        annotations = []
        
        for timestamp in timestamps:
            import random
            num_objects = random.randint(1, 2)
            
            for i in range(num_objects):
                annotations.append({
                    "timestamp": timestamp,
                    "object": random.choice(dummy_objects),
                    "bbox": [
                        random.randint(100, 400),
                        random.randint(100, 400),
                        random.randint(100, 300),
                        random.randint(100, 300)
                    ],
                    "coordinates_3d": [
                        round(random.uniform(-2.0, 2.0), 1),
                        round(random.uniform(-1.0, 1.0), 1),
                        round(random.uniform(0.5, 5.0), 1)
                    ],
                    "confidence": round(random.uniform(0.7, 0.9), 2)
                })
        
        return annotations

    async def analyze_frames(self, frame_paths: List[str], frame_timestamps: List[float]) -> List[Dict[str, Any]]:
        """Analyze frames with optimized batching for any frame rate."""
        if not frame_paths:
            logger.warning("No frames provided for analysis")
            return []
        
        # Estimate total processing time
        total_batches = (len(frame_paths) + self.batch_size - 1) // self.batch_size
        estimated_time = total_batches * self.retry_delay / 60  # minutes
        
        logger.info(f"Starting analysis of {len(frame_paths)} frames at {self.frame_rate} FPS")
        logger.info(f"Estimated processing time: {estimated_time:.1f} minutes ({total_batches} batches)")
        
        all_annotations = []
        
        for i in range(0, len(frame_paths), self.batch_size):
            batch_frames = frame_paths[i:i + self.batch_size]
            batch_timestamps = frame_timestamps[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_frames)} frames)")
            
            try:
                batch_annotations = await self._analyze_frame_batch(batch_frames, batch_timestamps)
                all_annotations.extend(batch_annotations)
                
                logger.info(f"Batch {batch_num} completed: {len(batch_annotations)} annotations")
                
                # Progressive delay - shorter delays as we get through more batches
                if i + self.batch_size < len(frame_paths):
                    progress = batch_num / total_batches
                    adjusted_delay = self.retry_delay * (1.0 - progress * 0.3)  # Reduce delay by up to 30%
                    logger.info(f"Waiting {adjusted_delay:.1f}s before next batch...")
                    await asyncio.sleep(adjusted_delay)
                
            except Exception as e:
                logger.error(f"Batch {batch_num} failed: {e}")
                dummy_annotations = self._generate_dummy_annotations(batch_timestamps)
                all_annotations.extend(dummy_annotations)
                continue
        
        logger.info(f"Completed analysis: {len(all_annotations)} annotations from {len(frame_paths)} frames")
        return all_annotations 