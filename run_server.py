#!/usr/bin/env python3
"""
Server runner for Video Annotation API - Phase 3
Starts the FastAPI server with async job processing and Gemini Pro Vision integration.
"""

import os
import sys
import uvicorn
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_dependencies():
    """Check that required dependencies are available."""
    logger.info("Checking dependencies...")
    
    # Check Gemini API key
    if not os.getenv('GEMINI_API_KEY'):
        logger.error("❌ GEMINI_API_KEY environment variable is required")
        logger.error("Please set your Gemini API key in .env file or environment")
        return False
    
    # Check FFmpeg
    if os.system("which ffmpeg > /dev/null 2>&1") != 0:
        logger.error("❌ FFmpeg is required but not found in PATH")
        logger.error("Please install FFmpeg: https://ffmpeg.org/download.html")
        return False
    
    # Check OpenCV
    try:
        import cv2
        logger.info(f"✅ OpenCV version: {cv2.__version__}")
    except ImportError:
        logger.error("❌ OpenCV is required but not installed")
        logger.error("Please install: pip install opencv-python")
        return False
    
    # Check Gemini SDK
    try:
        import google.generativeai as genai
        logger.info("✅ Google Generative AI SDK available")
    except ImportError:
        logger.error("❌ Google Generative AI SDK is required but not installed")
        logger.error("Please install: pip install google-generativeai")
        return False
    
    # Check PIL/Pillow
    try:
        from PIL import Image
        logger.info("✅ Pillow available")
    except ImportError:
        logger.error("❌ Pillow is required but not installed")
        logger.error("Please install: pip install pillow")
        return False
    
    logger.info("✅ All dependencies check passed")
    return True

def create_temp_directories():
    """Create necessary temporary directories."""
    temp_dirs = [
        "/tmp/video_processing",
        "./temp",
        "./logs"
    ]
    
    for temp_dir in temp_dirs:
        try:
            os.makedirs(temp_dir, exist_ok=True)
            logger.debug(f"Created temp directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to create temp directory {temp_dir}: {e}")

def main():
    """Main server startup function."""
    logger.info("🚀 Starting Video Annotation API - Phase 3")
    logger.info("Features: Async job processing with background workers and Gemini Pro Vision")
    
    # Check dependencies
    if not check_dependencies():
        logger.error("❌ Dependency check failed")
        sys.exit(1)
    
    # Create temporary directories
    create_temp_directories()
    
    # Configuration
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8000))
    reload = os.getenv('RELOAD', 'true').lower() == 'true'
    log_level = os.getenv('LOG_LEVEL', 'info').lower()
    
    logger.info(f"Server configuration:")
    logger.info(f"  Host: {host}")
    logger.info(f"  Port: {port}")
    logger.info(f"  Reload: {reload}")
    logger.info(f"  Log Level: {log_level}")
    
    # Start server
    try:
        logger.info("🌟 Starting FastAPI server...")
        logger.info(f"📍 API Documentation: http://{host}:{port}/api/docs")
        logger.info(f"🔍 API Info: http://{host}:{port}/api/info")
        logger.info(f"❤️  Health Check: http://{host}:{port}/api/health")
        logger.info(f"📋 Job Management: http://{host}:{port}/api/jobs")
        
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
            access_log=True,
            loop="asyncio"
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 