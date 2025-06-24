# backend/main.py
"""
Wolfstitch Cloud Backend - Enhanced Version with Full Download Support
Complete file processing API with storage and download capabilities
"""

import os
import sys
from pathlib import Path
import logging
import tempfile
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
import traceback
import hashlib
import json

# FastAPI imports
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('wolfstitch.log')
    ]
)
logger = logging.getLogger(__name__)

# Try to import enhanced modules with fallback
ENHANCED_PROCESSOR_AVAILABLE = False
WOLFCORE_AVAILABLE = False
STORAGE_AVAILABLE = False

try:
    from services.enhanced_processor import DocumentProcessor
    enhanced_processor = DocumentProcessor()
    ENHANCED_PROCESSOR_AVAILABLE = True
    logger.info("✅ Enhanced processor loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Enhanced processor not available: {e}")

try:
    from wolfcore import Wolfstitch as WOLFSTITCH_CLASS
    WOLFCORE_AVAILABLE = True
    logger.info("✅ Wolfcore loaded successfully")
except ImportError:
    logger.warning("⚠️ Wolfcore not available - using enhanced processor only")

try:
    from services.result_storage import storage_service
    STORAGE_AVAILABLE = True
    logger.info("✅ Storage service loaded successfully")
except ImportError:
    logger.warning("⚠️ Storage service not available")

# Create FastAPI app
app = FastAPI(
    title="Wolfstitch Cloud API",
    description="Enhanced document processing with full text extraction",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Wolfstitch Cloud Backend starting...")
    logger.info(f"   Enhanced Processor: {'✅' if ENHANCED_PROCESSOR_AVAILABLE else '❌'}")
    logger.info(f"   Wolfcore: {'✅' if WOLFCORE_AVAILABLE else '❌'}")
    logger.info(f"   Storage Service: {'✅' if STORAGE_AVAILABLE else '❌'}")
    
    if not ENHANCED_PROCESSOR_AVAILABLE and not WOLFCORE_AVAILABLE:
        logger.error("❌ No processing engines available!")
        sys.exit(1)

# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint with system status"""
    return {
        "name": "Wolfstitch Cloud API",
        "version": "2.0.0",
        "status": "operational",
        "engines": {
            "enhanced_processor": ENHANCED_PROCESSOR_AVAILABLE,
            "wolfcore": WOLFCORE_AVAILABLE,
            "storage": STORAGE_AVAILABLE
        }
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "enhanced_processor": ENHANCED_PROCESSOR_AVAILABLE,
            "wolfcore": WOLFCORE_AVAILABLE,
            "storage": STORAGE_AVAILABLE
        },
        "capabilities": {
            "formats": ["pdf", "docx", "txt", "md", "html", "epub", "csv", "xlsx", "pptx"],
            "max_file_size_mb": 100,
            "tokenizers": ["word-estimate", "char-estimate", "conservative"],
            "chunking_strategies": ["paragraph", "sentence", "line", "word"],
            "full_text_download": True
        }
    }

# Enhanced file processing endpoint
@app.post("/api/v1/quick-process")
async def quick_process_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tokenizer: Optional[str] = "word-estimate",
    max_tokens: Optional[int] = 1024
):
    """
    Quick file processing with preview results
    Returns truncated previews for fast response
    """
    return await _process_file_internal(
        background_tasks=background_tasks,
        file=file,
        tokenizer=tokenizer,
        max_tokens=max_tokens,
        return_full_chunks=False,
        store_results=True
    )

# Process and download endpoint
@app.post("/api/v1/process-and-download")
async def process_and_download_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tokenizer: Optional[str] = "word-estimate",
    max_tokens: Optional[int] = 1024,
    return_full_chunks: bool = Query(False)
):
    """
    Process file and optionally return full chunks
    Set return_full_chunks=true to get complete text content
    """
    return await _process_file_internal(
        background_tasks=background_tasks,
        file=file,
        tokenizer=tokenizer,
        max_tokens=max_tokens,
        return_full_chunks=return_full_chunks,
        store_results=True
    )

# Download stored results
@app.get("/api/v1/download/{job_id}")
async def download_results(
    job_id: str,
    format: Optional[str] = "jsonl"
):
    """
    Download complete processing results
    Retrieves full text content from storage
    """
    if not STORAGE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Storage service not available"
        )
    
    # Retrieve stored result
    result = await storage_service.get_result(job_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Results not found for job_id: {job_id}"
        )
    
    # Format response based on requested format
    if format == "jsonl":
        # Create JSONL content
        chunks = result.get("chunks", [])
        jsonl_lines = []
        
        for chunk in chunks:
            jsonl_lines.append(json.dumps({
                "text": chunk.get("text", ""),
                "chunk_id": chunk.get("chunk_id", chunk.get("chunk_index", 0) + 1),
                "tokens": chunk.get("token_count", 0),
                "word_count": chunk.get("word_count", 0),
                "metadata": {
                    "filename": result.get("filename", ""),
                    "job_id": job_id,
                    "processed_at": result.get("processing_time", ""),
                    "chunk_index": chunk.get("chunk_index", 0)
                }
            }))
        
        content = "\n".join(jsonl_lines)
        filename = f"{result.get('filename', 'document').replace('.', '_')}_full.jsonl"
        
        return StreamingResponse(
            iter([content]),
            media_type="application/jsonl",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    elif format == "json":
        # Return full JSON
        return JSONResponse(content=result)
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {format}"
        )

# List available results
@app.get("/api/v1/results")
async def list_results():
    """List all available processing results"""
    if not STORAGE_AVAILABLE:
        return {"results": [], "message": "Storage service not available"}
    
    results = await storage_service.list_results()
    return {"results": results, "count": len(results)}

# Internal processing function
async def _process_file_internal(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    tokenizer: str,
    max_tokens: int,
    return_full_chunks: bool,
    store_results: bool
):
    """Internal file processing logic"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    # Validate file size
    max_size = 100 * 1024 * 1024  # 100MB
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is 100MB, got {len(content) / 1024 / 1024:.1f}MB"
        )
    
    await file.seek(0)
    
    logger.info(f"📄 Processing file: {file.filename} ({len(content) / 1024 / 1024:.1f}MB)")
    
    file_ext = Path(file.filename).suffix.lower()
    temp_file = None
    
    try:
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=file_ext,
            prefix="wolfstitch_"
        )
        
        temp_file.write(content)
        temp_file.close()
        
        logger.debug(f"📁 Created temp file: {temp_file.name}")
        
        # Generate job ID
        job_id = f"job-{hashlib.md5(f'{file.filename}-{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:12]}"
        
        # Process with enhanced processor
        if ENHANCED_PROCESSOR_AVAILABLE:
            try:
                logger.info(f"🚀 Processing with enhanced processor: {file_ext}")
                
                result = await enhanced_processor.process_file(
                    temp_file.name,
                    max_tokens=max_tokens,
                    tokenizer=tokenizer
                )
                
                # Prepare chunks data
                full_chunks = [
                    {
                        "text": chunk["text"],
                        "chunk_id": chunk["chunk_id"],
                        "token_count": chunk["token_count"],
                        "word_count": chunk.get("word_count", len(chunk["text"].split())),
                        "chunk_index": chunk["chunk_index"]
                    }
                    for chunk in result.chunks
                ]
                
                # Store results if requested
                if store_results and STORAGE_AVAILABLE:
                    storage_data = {
                        "job_id": job_id,
                        "filename": file.filename,
                        "chunks": full_chunks,
                        "total_chunks": result.total_chunks,
                        "total_tokens": result.total_tokens,
                        "processing_time": result.processing_time,
                        "file_info": result.file_info,
                        "metadata": result.metadata
                    }
                    await storage_service.store_result(job_id, storage_data)
                
                # Prepare response
                if return_full_chunks:
                    # Return complete chunks
                    response_data = {
                        "job_id": job_id,
                        "filename": file.filename,
                        "total_chunks": result.total_chunks,
                        "total_tokens": result.total_tokens,
                        "processing_time": result.processing_time,
                        "status": "completed",
                        "enhanced": True,
                        "chunks": len(result.chunks),
                        "average_chunk_size": result.total_tokens // result.total_chunks if result.total_chunks > 0 else 0,
                        "data": full_chunks,  # Full chunks
                        "file_info": result.file_info,
                        "metadata": result.metadata,
                        "processing_method": "enhanced",
                        "full_chunks_included": True,
                        "download_url": f"/api/v1/download/{job_id}" if STORAGE_AVAILABLE else None
                    }
                else:
                    # Return preview only
                    preview_chunks = [
                        {
                            "text": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                            "tokens": chunk["token_count"],
                            "chunk_index": chunk["chunk_index"],
                            "word_count": chunk.get("word_count", len(chunk["text"].split()))
                        }
                        for chunk in result.chunks[:5]
                    ]
                    
                    response_data = {
                        "job_id": job_id,
                        "filename": file.filename,
                        "total_chunks": result.total_chunks,
                        "total_tokens": result.total_tokens,
                        "processing_time": result.processing_time,
                        "status": "completed",
                        "enhanced": True,
                        "chunks": len(result.chunks),
                        "average_chunk_size": result.total_tokens // result.total_chunks if result.total_chunks > 0 else 0,
                        "preview": preview_chunks,
                        "file_info": result.file_info,
                        "metadata": result.metadata,
                        "processing_method": "enhanced",
                        "full_chunks_included": False,
                        "download_url": f"/api/v1/download/{job_id}" if STORAGE_AVAILABLE else None
                    }
                
                logger.info(f"✅ Processing successful: {result.total_chunks} chunks, {result.total_tokens} tokens")
                
            except Exception as enhanced_error:
                logger.error(f"❌ Enhanced processing failed: {enhanced_error}")
                logger.debug(f"Traceback:\n{traceback.format_exc()}")
                
                # Try wolfcore fallback if available
                if WOLFCORE_AVAILABLE:
                    logger.info("🔄 Falling back to wolfcore")
                    response_data = await _wolfcore_fallback_processing(
                        temp_file.name, 
                        file.filename, 
                        tokenizer, 
                        max_tokens,
                        job_id
                    )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail={
                            "message": "Processing failed",
                            "error": str(enhanced_error)
                        }
                    )
        
        elif WOLFCORE_AVAILABLE:
            # Use wolfcore directly
            response_data = await _wolfcore_fallback_processing(
                temp_file.name, 
                file.filename, 
                tokenizer, 
                max_tokens,
                job_id
            )
        
        else:
            raise HTTPException(
                status_code=503,
                detail="No processing engine available"
            )
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_temp_file, temp_file.name)
        
        return response_data
        
    except HTTPException:
        if temp_file:
            background_tasks.add_task(cleanup_temp_file, temp_file.name)
        raise
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        logger.debug(f"Traceback:\n{traceback.format_exc()}")
        
        if temp_file:
            background_tasks.add_task(cleanup_temp_file, temp_file.name)
        
        raise HTTPException(
            status_code=500,
            detail={"message": "Unexpected error occurred", "error": str(e)}
        )

# Wolfcore fallback processing
async def _wolfcore_fallback_processing(
    temp_file_path: str, 
    filename: str, 
    tokenizer: str, 
    max_tokens: int,
    job_id: str
) -> dict:
    """Wolfcore fallback processing"""
    try:
        wf = WOLFSTITCH_CLASS()
        
        # Process file
        if hasattr(wf, 'process_file_async'):
            result = await wf.process_file_async(
                temp_file_path,
                tokenizer=tokenizer,
                max_tokens=max_tokens
            )
        else:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: wf.process_file(temp_file_path, tokenizer=tokenizer, max_tokens=max_tokens)
            )
        
        logger.info(f"✅ Wolfcore processing completed: {len(result.chunks)} chunks")
        
        return {
            "job_id": job_id,
            "filename": filename,
            "chunks": len(result.chunks),
            "total_chunks": len(result.chunks),
            "total_tokens": result.total_tokens,
            "average_chunk_size": result.total_tokens // len(result.chunks) if result.chunks else 0,
            "preview": [
                {
                    "text": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                    "tokens": getattr(chunk, 'token_count', 0)
                }
                for chunk in result.chunks[:5]
            ],
            "processing_method": "wolfcore",
            "enhanced": False,
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"Wolfcore processing failed: {e}")
        raise

# Cleanup function
async def cleanup_temp_file(file_path: str):
    """Clean up temporary file"""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.debug(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temp file {file_path}: {e}")

# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )