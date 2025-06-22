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
            "https://app.wolfstitch.dev",
            "https://dev.wolfstitch.dev"
        ]
    else:
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://www.wolfstitch.dev",
            "https://wolfstitch.dev",
            "https://dev.wolfstitch.dev"
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

# Add trusted host middleware for Railway
if settings.ENVIRONMENT.lower() == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["api.wolfstitch.dev", "*.railway.app", "*.up.railway.app"]
    )

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
        "api_version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Wolfstitch Cloud API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "quick_process": "/api/v1/quick-process"
        },
        "cors_enabled": True,
        "wolfcore_available": WOLFCORE_AVAILABLE
    }

# API endpoint for file processing
@app.post("/api/v1/quick-process")
async def quick_process(
    file: UploadFile = File(...),
    tokenizer: str = "word-estimate",
    max_tokens: int = 1024
):
    """Process a file and return chunks"""
    logger.info(f"📄 Processing file: {file.filename}")
    
    if not WOLFCORE_AVAILABLE:
        # Mock response for development/testing
        logger.warning("⚠️ Wolfcore not available, returning mock data")
        return {
            "message": "File processed successfully (mock mode)",
            "filename": file.filename,
            "chunks": 3,
            "total_tokens": 1847,
            "preview": [
                "This is the first chunk of your document. It contains the opening paragraphs and introduction to your content.",
                "This is the second chunk, containing the main body of your document with detailed explanations and examples.",
                "This is the final chunk with conclusions, references, and any appendices from your original document."
            ],
            "status": "completed"
        }
    
    try:
        # Create temporary file
        temp_file_path = None
        try:
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name
                logger.info(f"📁 Temporary file created: {temp_file_path}")
            
            # Process with Wolfstitch - FIXED: Remove asyncio.run() since we're already in async context
            logger.info(f"🧠 Processing with tokenizer: {tokenizer}, max_tokens: {max_tokens}")
            wolfstitch = WOLFSTITCH_CLASS()
            
            # Process the file synchronously (Wolfstitch is likely sync)
            result = wolfstitch.process_file(
                temp_file_path,
                tokenizer=tokenizer,
                max_tokens=max_tokens
            )
            
            # Extract data from result
            chunks = result.get('chunks', [])
            total_tokens = result.get('total_tokens', 0)
            
            # Create preview (first 3 chunks)
            preview = []
            for chunk in chunks[:3]:
                if isinstance(chunk, dict):
                    preview.append(chunk.get('text', str(chunk)))
                else:
                    preview.append(str(chunk))
            
            response_data = {
                "message": "File processed successfully",
                "filename": file.filename,
                "chunks": len(chunks),
                "total_tokens": total_tokens,
                "preview": preview,
                "status": "completed"
            }
            
            logger.info(f"✅ Processing completed: {len(chunks)} chunks, {total_tokens} tokens")
            return response_data
            
        finally:
            # Cleanup temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                logger.info(f"🗑️ Temporary file cleaned up: {temp_file_path}")
                
    except Exception as e:
        logger.error(f"❌ Processing failed: {str(e)}")
        # Enhanced error handling with more specific error types
        error_message = str(e)
        if "asyncio.run() cannot be called from a running event loop" in error_message:
            error_message = "Processing engine configuration error. Please try again."
        elif "No module named" in error_message:
            error_message = "Required processing libraries not available."
        elif "Permission denied" in error_message:
            error_message = "File access permission error. Please try a different file."
        
        raise HTTPException(
            status_code=500,
            detail={
                "message": "File processing failed",
                "error": error_message,
                "filename": file.filename
            }
        )

# Error handlers
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
    
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        log_level=settings.LOG_LEVEL.lower() if hasattr(settings, 'LOG_LEVEL') else "info",
        reload=settings.DEBUG if hasattr(settings, 'DEBUG') else False
    )