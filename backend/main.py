"""
Wolfstitch Cloud - FastAPI Application Entry Point
Railway-optimized deployment with enhanced error handling and dependency management
"""

import os
import sys
import tempfile
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

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
    
    # Create upload directory
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    os.makedirs(upload_dir, exist_ok=True)
    logger.info(f"📁 Upload directory ready: {upload_dir}")
    
    # Log configuration status
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🧠 Wolfcore available: {WOLFCORE_AVAILABLE}")
    logger.info(f"🐍 Python path: {sys.path[:3]}...")  # First 3 paths
    
    yield
    
    logger.info("🛑 Shutting down Wolfstitch Cloud API...")

# Determine CORS origins based on environment
def get_cors_origins():
    """Get CORS origins based on environment"""
    if settings.ENVIRONMENT.lower() == "production":
        return [
            "https://www.wolfstitch.dev",
            "https://wolfstitch.dev", 
            "https://app.wolfstitch.dev"
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
            "app.wolfstitch.dev",
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
        "port": os.getenv("PORT", "8000")
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
        "api_endpoints": "/api/v1/"
    }

# Import API routes
try:
    from backend.api.v1.main import api_router
    app.include_router(api_router, prefix="/api/v1")
    logger.info("✅ API routes successfully loaded")
except ImportError as e:
    logger.warning(f"⚠️ Failed to load API routes: {e}")
    
    # Fallback quick-process endpoint for Railway testing
    @app.post("/api/v1/quick-process")
    async def fallback_quick_process(file: UploadFile = File(...)):
        """Fallback quick process endpoint for testing"""
        logger.info(f"📁 Processing file: {file.filename}")
        
        if not WOLFCORE_AVAILABLE:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Wolfcore not available",
                    "message": "Service temporarily unavailable",
                    "filename": file.filename,
                    "environment": settings.ENVIRONMENT
                }
            )
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            # Initialize Wolfstitch
            wolfstitch = WOLFSTITCH_CLASS()
            
            # Process file
            result = wolfstitch.process_file(temp_file_path)
            
            # Clean up
            os.unlink(temp_file_path)
            
            return {
                "status": "success",
                "filename": file.filename,
                "result": result,
                "environment": settings.ENVIRONMENT
            }
            
        except Exception as e:
            logger.error(f"❌ Processing error: {e}")
            # Clean up on error
            if 'temp_file_path' in locals():
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Processing failed",
                    "message": str(e),
                    "filename": file.filename
                }
            )

# Custom error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "message": "Endpoint not found",
            "docs_url": "/docs",
            "available_endpoints": ["/", "/health", "/api/v1/quick-process"]
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
