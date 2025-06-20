"""
Wolfstitch Cloud - FastAPI Application Entry Point
Railway-compatible main application setup
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import os
import tempfile
import logging
from typing import Optional

# Import wolfcore with graceful fallback
try:
    from wolfcore import Wolfstitch
    WOLFCORE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Wolfcore import failed: {e}")
    WOLFCORE_AVAILABLE = False

# Import backend modules with graceful fallbacks
try:
    from backend.config import settings
except ImportError:
    # Fallback configuration for Railway
    class Settings:
        ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
        DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")
        SECRET_KEY = os.getenv("SECRET_KEY", "fallback-key")
    settings = Settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("🚀 Starting Wolfstitch Cloud API...")
    
    # Create upload directory
    os.makedirs("/tmp/uploads", exist_ok=True)
    
    yield
    
    logger.info("📴 Shutting down Wolfstitch Cloud API...")

# Create FastAPI app
app = FastAPI(
    title="Wolfstitch Cloud API",
    description="AI Dataset Preparation Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["https://*.railway.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """System health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "wolfcore_available": WOLFCORE_AVAILABLE
    }

# Root endpoint
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Welcome to Wolfstitch Cloud API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_url": "/health"
    }

# Quick process endpoint (simplified for Railway)
@app.post("/api/v1/quick-process")
async def quick_process(
    file: UploadFile = File(...),
    tokenizer: str = "word-estimate",
    max_tokens: int = 1024
):
    """Process uploaded file quickly"""
    try:
        if not WOLFCORE_AVAILABLE:
            return {
                "message": "Basic processing (wolfcore loading...)",
                "filename": file.filename,
                "status": "wolfcore_initializing"
            }
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Process with wolfcore
            wf = Wolfstitch()
            result = await wf.process_file_async(
                tmp_path,
                tokenizer=tokenizer,
                max_tokens=max_tokens
            )
            
            return {
                "message": "File processed successfully",
                "filename": file.filename,
                "chunks": len(result.chunks),
                "total_tokens": result.total_tokens,
                "preview": [chunk.text[:100] + "..." for chunk in result.chunks[:3]]
            }
            
        finally:
            # Cleanup temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        return {
            "message": "Processing failed",
            "error": str(e),
            "filename": file.filename
        }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "message": "Endpoint not found",
            "docs_url": "/docs"
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
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )

# Railway-compatible startup
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        log_level=settings.LOG_LEVEL.lower()
    )