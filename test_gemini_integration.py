"""
Test script for Phase 2 Gemini integration.
Validates the video annotation API with real Gemini processing.
"""

import asyncio
import logging
import os
import json
import time
from pathlib import Path
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class APITester:
    """Test suite for the video annotation API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_health_endpoint(self):
        """Test the health check endpoint."""
        logger.info("Testing health endpoint...")
        
        response = self.session.get(f"{self.base_url}/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        
        logger.info("✅ Health endpoint test passed")
        
    def test_api_info_endpoint(self):
        """Test the API info endpoint."""
        logger.info("Testing API info endpoint...")
        
        response = self.session.get(f"{self.base_url}/api/info")
        assert response.status_code == 200
        
        data = response.json()
        required_fields = [
            "gemini_configured", "default_frame_rate", 
            "default_chunk_duration", "gemini_batch_size"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        logger.info("✅ API info endpoint test passed")
        logger.info(f"Gemini configured: {data['gemini_configured']}")
        
    def test_video_annotation(self, video_url: str):
        """Test video annotation with a real video."""
        logger.info(f"Testing video annotation with: {video_url}")
        
        payload = {
            "video_url": video_url,
            "frame_rate": 1.0
        }
        
        start_time = time.time()
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/annotate",
                json=payload,
                timeout=300  # 5 minute timeout
            )
            
            processing_time = time.time() - start_time
            
            if response.status_code != 200:
                logger.error(f"API call failed with status {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
            
            data = response.json()
            
            # Validate response structure
            required_fields = [
                "status", "video_url", "duration_seconds", 
                "total_frames_processed", "processing_time_seconds", "annotations"
            ]
            
            for field in required_fields:
                assert field in data, f"Missing field: {field}"
            
            # Validate response data
            assert data["status"] in ["completed", "error"]
            assert isinstance(data["annotations"], list)
            assert data["total_frames_processed"] >= 0
            
            logger.info("✅ Video annotation test passed")
            logger.info(f"Status: {data['status']}")
            logger.info(f"Duration: {data['duration_seconds']}s")
            logger.info(f"Frames processed: {data['total_frames_processed']}")
            logger.info(f"Annotations found: {len(data['annotations'])}")
            logger.info(f"Processing time: {data['processing_time_seconds']}s")
            
            # Save results for inspection
            results_file = f"test_results_{int(time.time())}.json"
            with open(results_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Results saved to: {results_file}")
            
            # Validate annotation structure if any exist
            if data["annotations"]:
                sample_annotation = data["annotations"][0]
                annotation_fields = ["timestamp", "object", "bbox", "coordinates_3d", "confidence"]
                
                for field in annotation_fields:
                    assert field in sample_annotation, f"Missing annotation field: {field}"
                
                logger.info("✅ Annotation structure validation passed")
                logger.info(f"Sample annotation: {sample_annotation}")
            
            return True
            
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return False
        except AssertionError as e:
            logger.error(f"Validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Test failed: {e}")
            return False

def main():
    """Run the test suite."""
    logger.info("Starting Gemini integration tests...")
    
    # Check environment
    if not os.getenv('GEMINI_API_KEY'):
        logger.error("GEMINI_API_KEY not set. Please configure your API key.")
        return False
    
    tester = APITester()
    
    try:
        # Test basic endpoints
        tester.test_health_endpoint()
        tester.test_api_info_endpoint()
        
        # Test video annotation with a sample video
        test_video_url = "https://videodata3.s3.us-east-2.amazonaws.com/Medical+Content.mp4"
        
        logger.info("⚠️  Starting video annotation test - this may take several minutes...")
        success = tester.test_video_annotation(test_video_url)
        
        if success:
            logger.info("🎉 All tests passed! Gemini integration is working correctly.")
            return True
        else:
            logger.error("❌ Video annotation test failed.")
            return False
            
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 