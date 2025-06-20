"""
Wolfstitch Cloud - FastAPI Application Entry Point
Railway-compatible main application setup with secure CORS configuration
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

# Secure CORS configuration based on environment
def get_cors_origins():
    """Get CORS origins based on environment"""
    if settings.ENVIRONMENT == "development":
        # Development: Allow localhost + production domains for testing
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://www.wolfstitch.dev",
            "https://wolfstitch.dev"
        ]
    else:
        # Production: Only allow specific domains (no wildcards)
        return [
            "https://www.wolfstitch.dev",
            "https://wolfstitch.dev",
            "https://app.wolfstitch.dev"  # Future subdomain
        ]

# Apply CORS middleware with secure configuration
cors_origins = get_cors_origins()
logger.info(f"CORS origins configured: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization", 
        "Accept",
        "Origin",
        "X-Requested-With"
    ],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """System health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "wolfcore_available": WOLFCORE_AVAILABLE,
        "cors_origins": cors_origins
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
        logger.info(f"Processing file: {file.filename} from frontend")
        
        if not WOLFCORE_AVAILABLE:
            # Return a mock response when wolfcore isn't available
            return {
                "message": "File processed successfully (mock mode)",
                "filename": file.filename,
                "chunks": 12,
                "total_tokens": 1458,
                "preview": [
                    "This is a mock chunk of processed text from your document...",
                    "This is another mock chunk showing how the content would be split...",
                    "This is a third mock chunk demonstrating the chunking algorithm..."
                ],
                "status": "wolfcore_mock"
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
            
            logger.info(f"Processing completed: {len(result.chunks)} chunks, {result.total_tokens} tokens")
            
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
        return JSONResponse(
            status_code=500,
            content={
                "message": "Processing failed",
                "error": str(e),
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