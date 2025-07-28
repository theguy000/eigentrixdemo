"""
Main FastAPI application for video annotation with Gemini Pro Vision.
Phase 3: Async job processing system with background workers.
"""

import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

# Configure structured logging
def setup_logging():
    """Configure logging for the application."""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_format = os.getenv('LOG_FORMAT', 'standard')
    
    if log_format == 'json':
        # Structured JSON logging for production
        import json
        import datetime
        
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': datetime.datetime.utcnow().isoformat(),
                    'level': record.levelname,
                    'logger': record.name,
                    'message': record.getMessage(),
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno
                }
                if record.exc_info:
                    log_entry['exception'] = self.formatException(record.exc_info)
                return json.dumps(log_entry)
        
        formatter = JsonFormatter()
    else:
        # Standard logging format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('fastapi').setLevel(logging.INFO)
    logging.getLogger('services.gemini').setLevel(logging.INFO)
    logging.getLogger('app.video_processing').setLevel(logging.INFO)
    logging.getLogger('app.job_manager').setLevel(logging.INFO)
    logging.getLogger('app.background_worker').setLevel(logging.INFO)

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Validate required environment variables
def validate_config():
    """Validate that required configuration is present."""
    required_vars = ['GEMINI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info("Configuration validation passed")

# Validate configuration on startup
try:
    validate_config()
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    sys.exit(1)

# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    # Startup
    logger.info("🚀 Starting Video Annotation API - Phase 3")
    logger.info("Features: Async job processing with background workers")
    
    try:
        # Import here to avoid circular imports
        from .job_manager import job_manager
        from .background_worker import background_worker
        
        # Start job manager
        job_manager.start()
        logger.info("✅ Job manager started")
        
        # Start background worker
        background_worker.start()
        logger.info("✅ Background worker started")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to start services: {e}")
        raise
    finally:
        # Shutdown
        logger.info("🛑 Shutting down Video Annotation API")
        
        try:
            # Stop background worker
            background_worker.stop()
            logger.info("✅ Background worker stopped")
            
            # Stop job manager
            job_manager.stop()
            logger.info("✅ Job manager stopped")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")

# Import routes after logging setup
from .routes import router

# Create FastAPI app
app = FastAPI(
    title="Video Annotation API",
    description="AI-powered video annotation using Gemini Pro Vision with async job processing",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    """Log all HTTP requests."""
    import time
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} in {process_time:.3f}s")
    
    return response

# Include API routes
app.include_router(router)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Video Annotation API",
        "version": "3.0.0",
        "description": "AI-powered video annotation using Gemini Pro Vision",
        "phase": "Phase 3 - Async Job Processing",
        "features": [
            "Async job processing",
            "Background workers", 
            "Real-time status tracking",
            "Job management",
            "Gemini Pro Vision AI"
        ],
        "endpoints": {
            "create_job": "POST /api/annotate",
            "job_status": "GET /api/status/{job_id}",
            "list_jobs": "GET /api/jobs",
            "job_stats": "GET /api/jobs/stats",
            "health": "GET /api/health",
            "docs": "/api/docs"
        },
        "workflow": {
            "1": "POST /api/annotate → get job_id",
            "2": "Poll GET /api/status/{job_id} → check progress",
            "3": "When status='completed' → get annotations"
        }
    }

@app.get("/api/info")
async def api_info():
    """Get API configuration and status."""
    try:
        from .job_manager import job_manager
        from .background_worker import background_worker
        
        stats = job_manager.get_stats()
        
        return {
            "gemini_configured": bool(os.getenv('GEMINI_API_KEY')),
            "default_frame_rate": float(os.getenv('DEFAULT_FRAME_RATE', 1.0)),
            "default_chunk_duration": int(os.getenv('DEFAULT_CHUNK_DURATION', 300)),
            "max_video_duration": int(os.getenv('MAX_VIDEO_DURATION', 1200)),
            "gemini_batch_size": int(os.getenv('GEMINI_BATCH_SIZE', 15)),
            "job_processing": {
                "background_worker_running": background_worker.running,
                "max_concurrent_jobs": background_worker.max_concurrent_jobs,
                "total_jobs": stats["total_jobs"],
                "active_jobs": stats["status_breakdown"].get("processing", 0),
                "pending_jobs": stats["status_breakdown"].get("pending", 0)
            },
            "logging": {
                "level": os.getenv('LOG_LEVEL', 'INFO'),
                "format": os.getenv('LOG_FORMAT', 'standard')
            }
        }
    except Exception as e:
        logger.error(f"Failed to get API info: {e}")
        return {"error": "Failed to retrieve API information"}

# Health check for container orchestration
@app.get("/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 