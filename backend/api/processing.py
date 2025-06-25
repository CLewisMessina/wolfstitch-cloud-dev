# backend\api\processing.py
"""
Wolfstitch Cloud - Processing API
Enhanced with full processing capabilities for complete file exports
"""

import os
import uuid
import tempfile
import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Form, Depends
from fastapi.responses import JSONResponse

from backend.models.schemas import (
    ProcessingConfig,
    ProcessingStatus,
    JobStatusResponse,
    ProcessingResult
)
from backend.dependencies import get_current_user, get_rate_limiter
from backend.services.export_service import ExportService
from backend.services.storage_service import StorageService

logger = logging.getLogger(__name__)

# Initialize services
export_service = ExportService()
storage_service = StorageService()

router = APIRouter()

# Import wolfcore if available
try:
    from wolfcore import Wolfstitch
    WOLFCORE_AVAILABLE = True
except ImportError:
    logger.warning("Wolfcore not available - using basic processing")
    WOLFCORE_AVAILABLE = False

# In-memory job storage (will be replaced with Redis/DB in production)
processing_jobs: Dict[str, Dict[str, Any]] = {}


async def cleanup_temp_file(file_path: str):
    """Clean up temporary file after processing"""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.debug(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        logger.error(f"Error cleaning up temp file: {e}")


@router.post("/quick-process")
async def quick_process(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tokenizer: Optional[str] = Form("gpt-4"),
    max_tokens: Optional[int] = Form(1000),
    chunk_method: Optional[str] = Form("paragraph"),
    preserve_structure: Optional[bool] = Form(True),
    user=Depends(get_current_user),
    rate_limiter=Depends(get_rate_limiter)
):
    """
    Quick processing endpoint for previews (existing functionality)
    Returns first 3 chunks with truncated text for UI preview
    """
    # Rate limiting check
    if not await rate_limiter.check_processing_limit(user):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Create temporary file
    temp_file = None
    try:
        suffix = f".{file.filename.split('.')[-1]}" if '.' in file.filename else ""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_file = tmp.name
        
        logger.info(f"Processing file for preview: {file.filename}")
        
        if WOLFCORE_AVAILABLE:
            try:
                # Use wolfcore for processing
                wf = Wolfstitch()
                result = await wf.process_file_async(
                    temp_file,
                    tokenizer=tokenizer,
                    max_tokens=max_tokens,
                    chunk_method=chunk_method,
                    preserve_structure=preserve_structure
                )
                
                # Return preview response
                response_data = {
                    "job_id": f"quick-{uuid.uuid4().hex[:8]}",
                    "total_chunks": result.total_chunks,
                    "total_tokens": result.total_tokens,
                    "processing_time": result.processing_time,
                    "status": "completed",
                    "enhanced": True,
                    "chunks": [
                        {
                            "text": chunk.text[:100] if len(chunk.text) > 100 else chunk.text,
                            "token_count": chunk.token_count,
                            "chunk_index": chunk.chunk_index
                        }
                        for chunk in result.chunks[:3]  # Preview: first 3 chunks only
                    ],
                    "file_info": result.file_info,
                    "metadata": result.metadata
                }
                
            except Exception as e:
                logger.warning(f"Enhanced processing failed: {e}, falling back to basic")
                response_data = await _basic_processing_fallback(temp_file, file.filename)
        else:
            response_data = await _basic_processing_fallback(temp_file, file.filename)
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_temp_file, temp_file)
        
        logger.info(f"Preview processing completed: {response_data['total_chunks']} chunks")
        return response_data
        
    except Exception as e:
        logger.error(f"Processing error: {e}")
        if temp_file:
            background_tasks.add_task(cleanup_temp_file, temp_file)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/process-full")
async def process_full(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tokenizer: Optional[str] = Form("gpt-4"),
    max_tokens: Optional[int] = Form(1000),
    chunk_method: Optional[str] = Form("paragraph"),
    preserve_structure: Optional[bool] = Form(True),
    export_format: Optional[str] = Form("jsonl"),
    user=Depends(get_current_user),
    rate_limiter=Depends(get_rate_limiter)
):
    """
    Full processing endpoint that processes complete files without limits.
    Returns a job ID for tracking the processing status.
    """
    # Rate limiting check
    if not await rate_limiter.check_processing_limit(user):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Validate export format
    valid_formats = ["jsonl", "json", "csv"]
    if export_format not in valid_formats:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid export format. Must be one of: {', '.join(valid_formats)}"
        )
    
    # Create job ID
    job_id = f"job-{uuid.uuid4().hex}"
    
    # Initialize job status
    processing_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "filename": file.filename,
        "created_at": datetime.utcnow().isoformat(),
        "export_format": export_format,
        "user_id": user.user_id,
        "error": None,
        "result": None,
        "download_url": None
    }
    
    # Save uploaded file
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, f"{job_id}_{file.filename}")
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Process in background
    background_tasks.add_task(
        _process_file_background,
        job_id=job_id,
        file_path=file_path,
        filename=file.filename,
        config=ProcessingConfig(
            tokenizer=tokenizer,
            max_tokens=max_tokens,
            chunk_method=chunk_method,
            preserve_structure=preserve_structure
        ),
        export_format=export_format
    )
    
    # Return job information
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "File processing started. Use the job status endpoint to track progress.",
        "status_url": f"/api/v1/jobs/{job_id}/status"
    }


async def _process_file_background(
    job_id: str,
    file_path: str,
    filename: str,
    config: ProcessingConfig,
    export_format: str
):
    """
    Background task to process file completely without limits
    """
    try:
        # Update status to processing
        processing_jobs[job_id]["status"] = "processing"
        processing_jobs[job_id]["progress"] = 10
        
        logger.info(f"Starting full processing for job {job_id}, file: {filename}")
        
        if not WOLFCORE_AVAILABLE:
            raise Exception("Wolfcore not available for full processing")
        
        # Initialize processor
        wf = Wolfstitch()
        
        # Update progress
        processing_jobs[job_id]["progress"] = 20
        
        # Process file completely - NO LIMITS
        result = await wf.process_file_async(
            file_path,
            tokenizer=config.tokenizer,
            max_tokens=config.max_tokens,
            chunk_method=config.chunk_method,
            preserve_structure=config.preserve_structure
        )
        
        # Update progress
        processing_jobs[job_id]["progress"] = 70
        
        # Store complete result with ALL chunks
        processing_result = {
            "filename": filename,
            "total_chunks": result.total_chunks,
            "total_tokens": result.total_tokens,
            "total_characters": result.total_characters,
            "processing_time": result.processing_time,
            "chunks": [
                {
                    "chunk_id": idx + 1,
                    "text": chunk.text,  # FULL TEXT - NO TRUNCATION
                    "tokens": chunk.token_count,
                    "start_pos": getattr(chunk, 'start_pos', None),  # Safe attribute access
                    "end_pos": getattr(chunk, 'end_pos', None),      # Safe attribute access
                    "metadata": {
                        "chunk_method": config.chunk_method,
                        "tokenizer": config.tokenizer,
                        "chunk_index": getattr(chunk, 'chunk_index', idx)  # Use chunk_index if available
                    }
                }
                for idx, chunk in enumerate(result.chunks)  # ALL CHUNKS - NO LIMIT
            ],
            "file_info": result.file_info,
            "metadata": {
                **result.metadata,
                "export_format": export_format,
                "job_id": job_id,
                "processed_at": datetime.utcnow().isoformat()
            }
        }
        
        # Update progress
        processing_jobs[job_id]["progress"] = 90
        
        # Generate export file using export service
        export_info = await export_service.generate_export(
            job_id=job_id,
            processing_result=processing_result,
            export_format=export_format
        )
        
        # Store the export file and get download URL
        storage_info = await storage_service.store_export_file(
            source_path=Path(export_info["file_path"]),
            job_id=job_id,
            user_id=processing_jobs[job_id].get("user_id")
        )
        
        # Update job with download information
        processing_jobs[job_id]["download_url"] = storage_info["download_url"]
        processing_jobs[job_id]["export_info"] = export_info
        processing_jobs[job_id]["storage_info"] = storage_info
        
        # Store the result
        processing_jobs[job_id]["result"] = processing_result
        
        # Update job status
        processing_jobs[job_id]["status"] = "completed"
        processing_jobs[job_id]["progress"] = 100
        processing_jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
        
        # Clean up uploaded file
        if os.path.exists(file_path):
            os.unlink(file_path)
        
        logger.info(f"Full processing completed for job {job_id}: {result.total_chunks} chunks")
        
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}")
        processing_jobs[job_id]["status"] = "failed"
        processing_jobs[job_id]["error"] = str(e)
        processing_jobs[job_id]["failed_at"] = datetime.utcnow().isoformat()
        
        # Clean up on error
        if os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except:
                pass


async def _basic_processing_fallback(temp_file: str, filename: str):
    """Fallback to basic processing if enhanced modules unavailable"""
    try:
        with open(temp_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Basic chunking by paragraphs
        chunks = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        return {
            "job_id": f"basic-{uuid.uuid4().hex[:8]}",
            "total_chunks": len(chunks),
            "total_tokens": sum(len(chunk.split()) for chunk in chunks),
            "processing_time": 0.1,
            "status": "completed",
            "enhanced": False,
            "chunks": [
                {
                    "text": chunk[:100] if len(chunk) > 100 else chunk,
                    "token_count": len(chunk.split()),
                    "chunk_index": i
                }
                for i, chunk in enumerate(chunks[:3])
            ],
            "file_info": {
                "filename": filename,
                "size": os.path.getsize(temp_file)
            },
            "metadata": {
                "processor": "basic",
                "note": "Enhanced processing unavailable"
            }
        }
    except Exception as e:
        logger.error(f"Basic processing failed: {e}")
        raise


# Job status endpoint (basic implementation for now)
@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """Get the status of a processing job"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = processing_jobs[job_id]
    
    # Build response
    response = {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "filename": job["filename"],
        "created_at": job["created_at"],
        "export_format": job["export_format"]
    }
    
    # Add error info if failed
    if job["status"] == "failed":
        response["error"] = job["error"]
        response["failed_at"] = job.get("failed_at")
    
    # Add completion info if done
    elif job["status"] == "completed":
        response["completed_at"] = job.get("completed_at")
        response["download_url"] = job.get("download_url")
        response["total_chunks"] = job["result"]["total_chunks"] if job["result"] else None
        response["total_tokens"] = job["result"]["total_tokens"] if job["result"] else None
    
    return response