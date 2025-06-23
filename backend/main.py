# backend/main.py
"""
Wolfstitch Cloud - FastAPI Application Entry Point - FIXED VERSION
Railway-optimized deployment with robust document processing for ALL file types
"""

import os
import sys
import tempfile
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime

# Add project root to Python path for Railway
if '/app' not in sys.path:
    sys.path.insert(0, '/app')
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging early with enhanced debugging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Enhanced document processor import with comprehensive error handling
ENHANCED_PROCESSOR_AVAILABLE = False
enhanced_processor = None

try:
    from backend.services.enhanced_processor import DocumentProcessor
    enhanced_processor = DocumentProcessor()
    ENHANCED_PROCESSOR_AVAILABLE = True
    logger.info("✅ Enhanced processor successfully imported and initialized")
    logger.info(f"📋 Supported formats: {enhanced_processor.get_supported_formats()}")
    logger.info(f"📚 Available libraries: {enhanced_processor._get_available_libraries()}")
except ImportError as e:
    logger.warning(f"⚠️ Enhanced processor import failed: {e}")
    ENHANCED_PROCESSOR_AVAILABLE = False
except Exception as e:
    logger.error(f"❌ Enhanced processor initialization failed: {e}")
    ENHANCED_PROCESSOR_AVAILABLE = False

# Wolfcore fallback import
WOLFCORE_AVAILABLE = False
WOLFSTITCH_CLASS = None

try:
    from wolfcore import Wolfstitch
    WOLFSTITCH_CLASS = Wolfstitch
    WOLFCORE_AVAILABLE = True
    logger.info("✅ Wolfcore fallback successfully imported")
except ImportError as e:
    logger.warning(f"⚠️ Wolfcore fallback import failed: {e}")
    WOLFCORE_AVAILABLE = False

# Settings and configuration
settings = None
try:
    from backend.config.settings import get_settings
    settings = get_settings()
    logger.info(f"✅ Settings loaded: {settings.ENVIRONMENT}")
except ImportError as e:
    logger.warning(f"⚠️ Settings import failed: {e}")
    # Create minimal settings object
    class MinimalSettings:
        ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    settings = MinimalSettings()

# CORS and trusted hosts configuration
cors_origins = [
    "http://localhost:3000",
    "http://localhost:3001", 
    "https://wolfstitch.dev",
    "https://www.wolfstitch.dev",
    "https://app.wolfstitch.dev",
    "https://dev.wolfstitch.dev"
]

# Add Railway domains if available
railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
if railway_domain:
    cors_origins.extend([
        f"https://{railway_domain}",
        f"http://{railway_domain}"
    ])

trusted_hosts = ["*"]  # Allow all hosts for Railway deployment

# Application lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with startup and shutdown logic"""
    logger.info("🚀 Starting Wolfstitch Cloud API v2.0")
    logger.info(f"🔧 Enhanced processor: {'✅ Available' if ENHANCED_PROCESSOR_AVAILABLE else '❌ Unavailable'}")
    logger.info(f"🔄 Wolfcore fallback: {'✅ Available' if WOLFCORE_AVAILABLE else '❌ Unavailable'}")
    
    if not ENHANCED_PROCESSOR_AVAILABLE and not WOLFCORE_AVAILABLE:
        logger.warning("⚠️ No document processing engines available!")
    
    yield
    
    logger.info("🛑 Shutting down Wolfstitch Cloud API")

# FastAPI application
app = FastAPI(
    title="Wolfstitch Cloud API",
    description="Enhanced Document Processing API with Multi-format Support",
    version="2.0.0",
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=trusted_hosts
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Enhanced health check with processing engine status"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "environment": settings.ENVIRONMENT,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "cors_origins": cors_origins,
        "trusted_hosts": trusted_hosts,
        "railway_url": os.getenv("RAILWAY_PUBLIC_DOMAIN", "Not set"),
        "port": os.getenv("PORT", "8000"),
        "service": "wolfstitch-cloud-api",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "processing_engines": {
            "enhanced": ENHANCED_PROCESSOR_AVAILABLE,
            "wolfcore_fallback": WOLFCORE_AVAILABLE
        },
        "capabilities": {
            "enhanced_processor_formats": enhanced_processor.get_supported_formats() if ENHANCED_PROCESSOR_AVAILABLE else [],
            "enhanced_processor_libraries": enhanced_processor._get_available_libraries() if ENHANCED_PROCESSOR_AVAILABLE else {}
        }
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with comprehensive API information"""
    return {
        "message": "Wolfstitch Cloud API v2.0 - Enhanced Document Processing",
        "version": "2.0.0",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/health",
        "api_endpoints": "/api/v1/",
        "status": "operational",
        "processing_engines": {
            "enhanced_processor": "available" if ENHANCED_PROCESSOR_AVAILABLE else "unavailable",
            "wolfcore_fallback": "available" if WOLFCORE_AVAILABLE else "unavailable"
        },
        "features": {
            "enhanced_docx_processing": ENHANCED_PROCESSOR_AVAILABLE,
            "enhanced_pdf_processing": ENHANCED_PROCESSOR_AVAILABLE,
            "enhanced_excel_processing": ENHANCED_PROCESSOR_AVAILABLE,
            "enhanced_powerpoint_processing": ENHANCED_PROCESSOR_AVAILABLE,
            "enhanced_html_processing": ENHANCED_PROCESSOR_AVAILABLE,
            "enhanced_epub_processing": ENHANCED_PROCESSOR_AVAILABLE,
            "multi_format_support": ENHANCED_PROCESSOR_AVAILABLE,
            "comprehensive_debugging": True
        },
        "supported_formats": enhanced_processor.get_supported_formats() if ENHANCED_PROCESSOR_AVAILABLE else ["txt"],
        "processing_info": {
            "max_file_size": "100MB",
            "supported_tokenizers": ["word-estimate", "char-estimate", "conservative"],
            "chunking_strategies": ["paragraph", "sentence", "line", "word"],
            "output_formats": ["JSON", "chunks with metadata"]
        }
    }

# Enhanced file processing endpoint with comprehensive error handling
@app.post("/api/v1/quick-process")
async def quick_process_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tokenizer: Optional[str] = "word-estimate",
    max_tokens: Optional[int] = 1024
):
    """
    Enhanced file processing with robust format support for ALL file types
    Supports DOCX, PDF, Excel, PowerPoint, HTML, EPUB, CSV, TXT, Markdown, Code files
    """
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
    
    # Reset file pointer for downstream processing
    await file.seek(0)
    
    logger.info(f"📄 Processing file: {file.filename} ({len(content) / 1024 / 1024:.1f}MB)")
    
    # Create temporary file with proper extension
    file_ext = Path(file.filename).suffix.lower()
    temp_file = None
    
    try:
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=file_ext,
            prefix="wolfstitch_"
        )
        
        # Write content to temp file
        temp_file.write(content)
        temp_file.close()
        
        logger.debug(f"📁 Created temp file: {temp_file.name}")
        
        # Process with enhanced processor if available
        if ENHANCED_PROCESSOR_AVAILABLE:
            try:
                logger.info(f"🚀 Processing with enhanced processor: {file_ext}")
                
                result = await enhanced_processor.process_file(
                    temp_file.name,
                    max_tokens=max_tokens,
                    tokenizer=tokenizer
                )
                
                # Convert to API response format
                response_data = {
                    "job_id": f"enhanced-{hash(file.filename)}",
                    "filename": file.filename,
                    "total_chunks": result.total_chunks,
                    "total_tokens": result.total_tokens,
                    "processing_time": result.processing_time,
                    "status": "completed",
                    "enhanced": True,
                    "chunks": len(result.chunks),
                    "average_chunk_size": result.total_tokens // result.total_chunks if result.total_chunks > 0 else 0,
                    "preview": [
                        {
                            "text": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                            "tokens": chunk["token_count"],
                            "chunk_index": chunk["chunk_index"],
                            "word_count": chunk.get("word_count", len(chunk["text"].split()))
                        }
                        for chunk in result.chunks[:5]  # First 5 chunks for preview
                    ],
                    "file_info": result.file_info,
                    "metadata": result.metadata,
                    "processing_method": "enhanced",
                    "extraction_success": True
                }
                
                logger.info(f"✅ Enhanced processing successful: {result.total_chunks} chunks, {result.total_tokens} tokens")
                
            except Exception as enhanced_error:
                logger.error(f"❌ Enhanced processing failed: {enhanced_error}")
                logger.debug(f"Enhanced processing traceback:\n{traceback.format_exc()}")
                
                # Fall back to wolfcore if available
                if WOLFCORE_AVAILABLE:
                    logger.info("🔄 Falling back to wolfcore processing")
                    response_data = await _wolfcore_fallback_processing(temp_file.name, file.filename, tokenizer, max_tokens)
                else:
                    # No fallback available
                    raise HTTPException(
                        status_code=500,
                        detail={
                            "message": "Enhanced processing failed and no fallback available",
                            "error": str(enhanced_error),
                            "filename": file.filename,
                            "suggestion": "Please try a different file or check file format"
                        }
                    )
        
        elif WOLFCORE_AVAILABLE:
            # Use wolfcore processing
            logger.info(f"🔄 Processing with wolfcore fallback: {file_ext}")
            response_data = await _wolfcore_fallback_processing(temp_file.name, file.filename, tokenizer, max_tokens)
        
        else:
            # No processing engines available
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "No document processing engine available",
                    "enhanced_processor": ENHANCED_PROCESSOR_AVAILABLE,
                    "wolfcore_available": WOLFCORE_AVAILABLE,
                    "suggestion": "Please check server configuration and dependencies"
                }
            )
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_temp_file, temp_file.name)
        
        logger.info(f"🎉 Processing completed successfully: {response_data.get('total_chunks', 0)} chunks")
        return response_data
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        if temp_file:
            background_tasks.add_task(cleanup_temp_file, temp_file.name)
        raise
    
    except Exception as e:
        logger.error(f"❌ Unexpected processing error: {e}")
        logger.debug(f"Processing error traceback:\n{traceback.format_exc()}")
        
        if temp_file:
            background_tasks.add_task(cleanup_temp_file, temp_file.name)
        
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unexpected processing error occurred",
                "error": str(e),
                "filename": file.filename,
                "suggestion": "Please try again or contact support if the problem persists"
            }
        )

async def _wolfcore_fallback_processing(temp_file_path: str, filename: str, tokenizer: str, max_tokens: int) -> dict:
    """Wolfcore fallback processing with error handling"""
    try:
        wf = WOLFSTITCH_CLASS()
        
        # Try async processing first
        if hasattr(wf, 'process_file_async'):
            logger.debug("Using async wolfcore processing")
            result = await wf.process_file_async(
                temp_file_path,
                tokenizer=tokenizer,
                max_tokens=max_tokens
            )
        else:
            logger.debug("Using sync wolfcore processing")
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: wf.process_file(temp_file_path, tokenizer=tokenizer, max_tokens=max_tokens)
            )
        
        logger.info(f"✅ Wolfcore processing completed: {len(result.chunks)} chunks, {result.total_tokens} tokens")
        
        return {
            "job_id": f"wolfcore-{hash(filename)}",
            "filename": filename,
            "chunks": len(result.chunks),
            "total_chunks": len(result.chunks),
            "total_tokens": result.total_tokens,
            "average_chunk_size": result.total_tokens // len(result.chunks) if result.chunks else 0,
            "preview": [
                {
                    "text": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                    "tokens": getattr(chunk, 'token_count', getattr(chunk, 'tokens', 0))
                }
                for chunk in result.chunks[:5]
            ],
            "processing_method": "wolfcore_fallback",
            "enhanced": False,
            "status": "completed",
            "processing_time": getattr(result, 'processing_time', 1.0),
            "extraction_success": True
        }
        
    except Exception as e:
        logger.error(f"❌ Wolfcore fallback processing failed: {e}")
        raise


async def cleanup_temp_file(file_path: str):
    """Clean up temporary file"""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.debug(f"🗑️ Cleaned up temp file: {file_path}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to cleanup temp file {file_path}: {e}")

# Import additional API routes if available
try:
    from backend.api.v1.main import api_router
    app.include_router(api_router, prefix="/api/v1")
    logger.info("✅ Additional API routes successfully loaded")
except ImportError as e:
    logger.info(f"ℹ️ Additional API routes not available: {e}")

# Development and testing endpoints
if settings and hasattr(settings, 'ENVIRONMENT') and settings.ENVIRONMENT.lower() in ["development", "testing"]:
    
    @app.get("/api/v1/test-processor")
    async def test_processor():
        """Test processor capabilities and configuration"""
        
        test_results = {
            "enhanced_processor": {
                "available": ENHANCED_PROCESSOR_AVAILABLE,
                "supported_formats": enhanced_processor.get_supported_formats() if ENHANCED_PROCESSOR_AVAILABLE else [],
                "libraries": enhanced_processor._get_available_libraries() if ENHANCED_PROCESSOR_AVAILABLE else {}
            },
            "wolfcore_fallback": {
                "available": WOLFCORE_AVAILABLE,
                "class_available": WOLFSTITCH_CLASS is not None
            },
            "system_info": {
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "environment": settings.ENVIRONMENT,
                "temp_dir": tempfile.gettempdir(),
                "working_dir": os.getcwd()
            }
        }
        
        return test_results
    
    @app.post("/api/v1/test-file-upload")
    async def test_file_upload(file: UploadFile = File(...)):
        """Test file upload without processing"""
        content = await file.read()
        
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": len(content),
            "size_mb": round(len(content) / 1024 / 1024, 2),
            "file_extension": Path(file.filename).suffix.lower(),
            "upload_successful": True
        }

# Custom error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler with helpful information"""
    return JSONResponse(
        status_code=404,
        content={
            "message": "Endpoint not found",
            "docs_url": "/docs",
            "available_endpoints": [
                "/",
                "/health", 
                "/api/v1/quick-process",
                "/api/v1/test-processor" if settings.ENVIRONMENT != "production" else None
            ],
            "suggestion": "Check the API documentation at /docs"
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler with debugging information"""
    logger.error(f"Internal server error: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
            "suggestion": "Please try again or contact support if the problem persists",
            "processing_engines_available": {
                "enhanced_processor": ENHANCED_PROCESSOR_AVAILABLE,
                "wolfcore_fallback": WOLFCORE_AVAILABLE
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )

# Railway-compatible startup
if __name__ == "__main__":
    import traceback
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"🚀 Starting Wolfstitch Cloud API v2.0")
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🌐 Server: {host}:{port}")
    logger.info(f"🔧 CORS origins: {cors_origins}")
    logger.info(f"🔒 Trusted hosts: {trusted_hosts}")
    logger.info(f"🧠 Enhanced processor: {'✅ Available' if ENHANCED_PROCESSOR_AVAILABLE else '❌ Unavailable'}")
    logger.info(f"🔄 Wolfcore fallback: {'✅ Available' if WOLFCORE_AVAILABLE else '❌ Unavailable'}")
    
    if ENHANCED_PROCESSOR_AVAILABLE:
        logger.info(f"📋 Supported formats: {len(enhanced_processor.get_supported_formats())} formats")
        logger.info(f"📚 Libraries: {enhanced_processor._get_available_libraries()}")
    
    try:
        uvicorn.run(
            "backend.main:app",
            host=host,
            port=port,
            log_level=settings.LOG_LEVEL.lower() if hasattr(settings, 'LOG_LEVEL') else "info",
            reload=settings.DEBUG if hasattr(settings, 'DEBUG') else False,
            access_log=True
        )
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        logger.debug(f"Startup error traceback:\n{traceback.format_exc()}")
        sys.exit(1)
