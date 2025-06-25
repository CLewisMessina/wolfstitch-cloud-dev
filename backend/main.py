# backend/main.py
"""
Wolfstitch Cloud - FastAPI Application Entry Point
Railway-optimized deployment with enhanced error handling and dependency management
Updated with full processing and download functionality
"""

import os
import sys
import tempfile
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path

# Add project root to Python path for Railway
if '/app' not in sys.path:
    sys.path.insert(0, '/app')
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging early
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global variables for dependencies
WOLFCORE_AVAILABLE = False
WOLFSTITCH_CLASS = None
settings = None

def initialize_dependencies():
    """Initialize all dependencies with graceful fallbacks"""
    global WOLFCORE_AVAILABLE, WOLFSTITCH_CLASS, settings
    
    # Try to import wolfcore
    try:
        from wolfcore import Wolfstitch
        WOLFSTITCH_CLASS = Wolfstitch
        WOLFCORE_AVAILABLE = True
        logger.info("✅ Wolfcore successfully imported")
    except ImportError as e:
        logger.warning(f"⚠️ Wolfcore import failed: {e}")
        logger.warning("🔧 Continuing with limited functionality")
        WOLFCORE_AVAILABLE = False

    # Try to import settings
    try:
        from backend.config import settings as app_settings
        settings = app_settings
        logger.info("✅ Backend config successfully imported")
    except ImportError as e:
        logger.warning(f"⚠️ Backend config import failed: {e}")
        # Fallback configuration for Railway
        class Settings:
            ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
            DEBUG = os.getenv("DEBUG", "false").lower() == "true"
            LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
            ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")
            SECRET_KEY = os.getenv("SECRET_KEY", "fallback-railway-key")
        settings = Settings()
        logger.info("🔧 Using fallback configuration")

# Initialize dependencies
initialize_dependencies()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 Starting Wolfstitch Cloud API...")
    
    # Create required directories
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    export_dir = os.getenv("EXPORT_DIR", "./exports")
    storage_dir = os.getenv("STORAGE_DIR", "./storage")
    
    for directory in [upload_dir, export_dir, storage_dir]:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"📁 Directory ready: {directory}")
    
    # Initialize services for cleanup tasks
    cleanup_task_handle = None
    try:
        from backend.services.storage_service import StorageService
        from backend.services.export_service import ExportService
        
        storage_service = StorageService(storage_dir=storage_dir)
        export_service = ExportService(export_dir=export_dir)
        
        # Start background cleanup task
        async def cleanup_task():
            while True:
                try:
                    await asyncio.sleep(3600)  # Run every hour
                    await storage_service.cleanup_expired_files()
                    await export_service.cleanup_old_exports()
                    logger.info("🧹 Cleanup task completed")
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")
        
        cleanup_task_handle = asyncio.create_task(cleanup_task())
        logger.info("🧹 Cleanup task started")
    except ImportError:
        logger.warning("⚠️ Services not available for cleanup tasks")
    
    # Log configuration status
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🧠 Wolfcore available: {WOLFCORE_AVAILABLE}")
    logger.info(f"🐍 Python path: {sys.path[:3]}...")  # First 3 paths
    
    yield
    
    # Cancel cleanup task on shutdown
    if cleanup_task_handle:
        cleanup_task_handle.cancel()
        try:
            await cleanup_task_handle
        except asyncio.CancelledError:
            pass
    
    logger.info("🛑 Shutting down Wolfstitch Cloud API...")

# Determine CORS origins based on environment
def get_cors_origins():
    """Get CORS origins based on environment"""
    if settings.ENVIRONMENT.lower() == "production":
        return [
            "https://www.wolfstitch.dev",
            "https://wolfstitch.dev"
        ]
    else:
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://www.wolfstitch.dev",
            "https://wolfstitch.dev",
            "https://dev.wolfstitch.dev",
            "https://api-dev.wolfstitch.dev"
        ]

# Get trusted hosts based on environment
def get_trusted_hosts():
    """Get trusted hosts based on environment and Railway configuration"""
    # Base hosts that are always allowed
    base_hosts = [
        "*.railway.app", 
        "*.up.railway.app",
        "localhost",
        "127.0.0.1"
    ]
    
    if settings.ENVIRONMENT.lower() == "production":
        return base_hosts + [
            "api.wolfstitch.dev",
            "wolfstitch.dev",
            "www.wolfstitch.dev"
        ]
    else:
        # Development/staging environment
        return base_hosts + [
            "api-dev.wolfstitch.dev",
            "dev.wolfstitch.dev", 
            "qmtm3lpm.up.railway.app",  # Your actual Railway staging backend URL
            "hdxldm16.up.railway.app"   # Your actual Railway staging frontend URL
        ]

# Create FastAPI application
app = FastAPI(
    title="Wolfstitch Cloud API",
    description="AI Dataset Preparation Platform - Cloud Native",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
cors_origins = get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin"]
)

# Add trusted host middleware with proper configuration
trusted_hosts = get_trusted_hosts()
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=trusted_hosts
)

# Log configuration for debugging
logger.info(f"🔧 CORS origins: {cors_origins}")
logger.info(f"🔒 Trusted hosts: {trusted_hosts}")
logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Railway and monitoring"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "wolfcore_available": WOLFCORE_AVAILABLE,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "cors_origins": cors_origins,
        "trusted_hosts": trusted_hosts,
        "railway_url": os.getenv("RAILWAY_PUBLIC_DOMAIN", "Not set"),
        "port": os.getenv("PORT", "8000"),
        "service": "wolfstitch-cloud-api",
        "timestamp": asyncio.get_event_loop().time()
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Wolfstitch Cloud API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/health",
        "api_endpoints": "/api/v1/",
        "status": "operational",
        "wolfcore_status": "available" if WOLFCORE_AVAILABLE else "unavailable"
    }

# Import and register API routes
try:
    from backend.api import processing, downloads
    
    # Register processing routes (includes both quick-process and process-full)
    app.include_router(processing.router, prefix="/api/v1", tags=["processing"])
    
    # Register download routes
    app.include_router(downloads.router, prefix="/api/v1/downloads", tags=["downloads"])
    
    logger.info("✅ API routes successfully loaded")
except ImportError as e:
    logger.warning(f"⚠️ Failed to load API routes: {e}")
    
    # Fallback quick-process endpoint if routes fail to load
    @app.post("/api/v1/quick-process")
    async def quick_process_file(
        file: UploadFile = File(...),
        tokenizer: Optional[str] = "gpt-4",
        max_tokens: Optional[int] = 1000
    ):
        """
        Process uploaded file into chunks
        Supports 40+ file formats when wolfcore is available
        """
        if not WOLFCORE_AVAILABLE:
            logger.error("Wolfcore not available for file processing")
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "File processing service unavailable",
                    "error": "Wolfcore dependency not loaded",
                    "suggestion": "Please check server configuration"
                }
            )
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file selected")
        
        # Validate file size (100MB limit)
        max_size = 100 * 1024 * 1024  # 100MB
        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is 100MB, got {len(content) / 1024 / 1024:.1f}MB"
            )
        
        # Reset file pointer
        await file.seek(0)
        
        logger.info(f"Processing file: {file.filename} ({len(content)} bytes)")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=f".{file.filename.split('.')[-1]}" if '.' in file.filename else ""
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Process with wolfcore
            wf = WOLFSTITCH_CLASS()
            result = wf.process_file(
                file_path=tmp_path,
                tokenizer=tokenizer,
                max_tokens=max_tokens
            )
            
            logger.info(f"✅ Successfully processed {file.filename}: {result.total_chunks} chunks")
            
            return {
                "filename": file.filename,
                "total_chunks": result.total_chunks,
                "total_tokens": result.total_tokens,
                "chunks_preview": [
                    {
                        "text": chunk.text[:100] if len(chunk.text) > 100 else chunk.text,
                        "tokens": getattr(chunk, 'tokens', 0)
                    }
                    for chunk in result.chunks[:3]
                ],
                "environment": settings.ENVIRONMENT
            }
            
        except Exception as e:
            logger.error(f"❌ Processing failed for {file.filename}: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "message": "File processing failed",
                    "error": str(e),
                    "filename": file.filename,
                    "suggestion": "Please try a different file or contact support"
                }
            )
        finally:
            # Cleanup temp file
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Failed to cleanup temp file: {cleanup_error}")

# Try to import additional API routes if available
try:
    from backend.api.v1.main import api_router
    app.include_router(api_router, prefix="/api/v1")
    logger.info("✅ Additional API routes loaded")
except ImportError:
    logger.info("ℹ️ Additional API routes not available")

# Advanced processing endpoint placeholder
@app.post("/api/v1/process")
async def process_file_advanced(
    file: UploadFile = File(...),
    config: Optional[dict] = None
):
    """Advanced file processing with custom configuration"""
    # This is now handled by the processing.router if loaded
    # Otherwise, return placeholder message
    return {
        "message": "Advanced processing endpoint - use /api/v1/process-full for full processing",
        "filename": file.filename,
        "status": "redirect_to_process_full"
    }

# Custom error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "message": "Endpoint not found",
            "docs_url": "/docs",
            "available_endpoints": [
                "/", 
                "/health", 
                "/api/v1/quick-process",
                "/api/v1/process-full",
                "/api/v1/jobs/{job_id}/status",
                "/api/v1/downloads/{storage_id}/{filename}"
            ]
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler"""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
            "suggestion": "Please try again or contact support if the problem persists"
        }
    )

# Railway-compatible startup
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"🚀 Starting server on {host}:{port}")
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🔧 CORS origins: {cors_origins}")
    logger.info(f"🔒 Trusted hosts: {trusted_hosts}")
    
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        log_level=settings.LOG_LEVEL.lower() if hasattr(settings, 'LOG_LEVEL') else "info",
        reload=settings.DEBUG if hasattr(settings, 'DEBUG') else False
    )