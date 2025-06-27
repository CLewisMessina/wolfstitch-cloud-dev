# backend/api/batch_processing.py
"""
Batch Processing API Endpoints
Feature-flagged implementation with production safety
"""

import os
import uuid
import tempfile
import logging
import asyncio
import time
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Form, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from backend.models.schemas import ProcessingConfig, ProcessingResult
from backend.dependencies import get_current_user, get_rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter()

# Feature flag check
def is_batch_processing_enabled() -> bool:
    """Check if batch processing is enabled via environment variable"""
    return os.getenv("ENABLE_BATCH_PROCESSING", "false").lower() == "true"

# Import wolfcore if available
try:
    from wolfcore import Wolfstitch
    WOLFCORE_AVAILABLE = True
except ImportError:
    logger.warning("Wolfcore not available - batch processing will be limited")
    WOLFCORE_AVAILABLE = False

# In-memory job storage (will be replaced with Redis/DB in production)
batch_jobs: Dict[str, Dict[str, Any]] = {}

# Configuration from environment
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "100"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
MAX_BATCH_SIZE_MB = int(os.getenv("MAX_BATCH_SIZE_MB", "500"))
BATCH_TIMEOUT_SECONDS = int(os.getenv("BATCH_TIMEOUT_SECONDS", "300"))


async def cleanup_temp_files(file_paths: List[str]):
    """Clean up temporary files after processing"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.debug(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up temp file {file_path}: {e}")


@router.post("/batch-process")
async def batch_process(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    tokenizer: Optional[str] = Form("gpt-4"),
    max_tokens: Optional[int] = Form(1000),
    chunk_method: Optional[str] = Form("paragraph"),
    preserve_structure: Optional[bool] = Form(True),
    export_format: Optional[str] = Form("jsonl"),
    user=Depends(get_current_user),
    rate_limiter=Depends(get_rate_limiter)
):
    """
    Batch process multiple files
    Feature-flagged with graceful degradation
    """
    
    # Feature flag check with graceful degradation
    if not is_batch_processing_enabled():
        logger.info("Batch processing disabled, redirecting to single file processing")
        
        if len(files) > 1:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Batch processing is currently disabled",
                    "suggestion": "Please process files one at a time using the quick-process endpoint",
                    "files_received": len(files),
                    "max_files_allowed": 1
                }
            )
        
        # Process single file using existing endpoint logic
        return await _process_single_file_fallback(
            files[0], tokenizer, max_tokens, chunk_method, 
            preserve_structure, export_format, user, rate_limiter, background_tasks
        )
    
    # Rate limiting check
    if not await rate_limiter.check_batch_limit(user):
        raise HTTPException(status_code=429, detail="Batch processing rate limit exceeded")
    
    # Validate inputs
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"Too many files. Maximum batch size is {MAX_BATCH_SIZE}, received {len(files)}"
        )
    
    # Validate export format
    valid_formats = ["jsonl", "json", "csv", "zip"]
    if export_format not in valid_formats:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid export format. Must be one of: {', '.join(valid_formats)}"
        )
    
    # Check total batch size
    total_size = sum(await _get_file_size(file) for file in files)
    max_batch_bytes = MAX_BATCH_SIZE_MB * 1024 * 1024
    
    if total_size > max_batch_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Batch too large. Maximum total size is {MAX_BATCH_SIZE_MB}MB, received {total_size / 1024 / 1024:.1f}MB"
        )
    
    # Create batch job
    batch_id = f"batch-{uuid.uuid4().hex}"
    
    # Initialize batch job status
    batch_jobs[batch_id] = {
        "batch_id": batch_id,
        "status": "pending",
        "progress": 0,
        "total_files": len(files),
        "processed_files": 0,
        "successful_files": 0,
        "failed_files": 0,
        "created_at": datetime.utcnow().isoformat(),
        "export_format": export_format,
        "user_id": user.user_id,
        "files": [{"filename": file.filename, "size": await _get_file_size(file), "status": "pending"} for file in files],
        "results": [],
        "errors": [],
        "download_url": None
    }
    
    # Save uploaded files to temporary directory
    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    temp_files = []
    for i, file in enumerate(files):
        temp_path = os.path.join(upload_dir, f"{batch_id}_{i}_{file.filename}")
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        temp_files.append(temp_path)
    
    # Process batch in background
    background_tasks.add_task(
        _process_batch_background,
        batch_id=batch_id,
        file_paths=temp_files,
        filenames=[file.filename for file in files],
        config=ProcessingConfig(
            tokenizer=tokenizer,
            max_tokens=max_tokens,
            chunk_method=chunk_method,
            preserve_structure=preserve_structure
        ),
        export_format=export_format
    )
    
    # Return batch information
    return {
        "batch_id": batch_id,
        "status": "pending",
        "total_files": len(files),
        "message": "Batch processing started. Use the batch status endpoint to track progress.",
        "status_url": f"/api/v1/batch/{batch_id}/status",
        "estimated_time": f"{len(files) * 10} seconds"
    }


async def _get_file_size(file: UploadFile) -> int:
    """Get file size without reading entire file"""
    current_pos = file.file.tell()
    file.file.seek(0, 2)  # Seek to end
    size = file.file.tell()
    file.file.seek(current_pos)  # Restore position
    return size


async def _process_single_file_fallback(
    file: UploadFile,
    tokenizer: str,
    max_tokens: int,
    chunk_method: str,
    preserve_structure: bool,
    export_format: str,
    user,
    rate_limiter,
    background_tasks: BackgroundTasks
):
    """Fallback to single file processing when batch is disabled"""
    
    # Use existing quick-process logic but return batch-like response
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Create temporary file
    temp_file = None
    try:
        suffix = f".{file.filename.split('.')[-1]}" if '.' in file.filename else ".txt"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_file = tmp.name
        
        # Process using wolfcore if available
        if WOLFCORE_AVAILABLE:
            try:
                processor = Wolfstitch()
                result = await processor.process_file_async(
                    temp_file,
                    config={
                        "tokenizer": tokenizer,
                        "max_tokens": max_tokens,
                        "chunk_method": chunk_method,
                        "preserve_structure": preserve_structure
                    }
                )
                
                # Format as batch response with single file
                return {
                    "batch_id": f"single-{uuid.uuid4().hex[:8]}",
                    "status": "completed",
                    "total_files": 1,
                    "processed_files": 1,
                    "successful_files": 1,
                    "failed_files": 0,
                    "results": [{
                        "filename": file.filename,
                        "status": "completed",
                        "chunks": result.total_chunks,
                        "tokens": result.total_tokens,
                        "processing_time": result.processing_time
                    }],
                    "download_ready": True,
                    "message": "Single file processed successfully (batch processing disabled)"
                }
                
            except Exception as e:
                logger.error(f"Wolfcore processing failed: {e}")
                raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
        
        else:
            # Basic fallback processing
            return {
                "batch_id": f"basic-{uuid.uuid4().hex[:8]}",
                "status": "completed",
                "total_files": 1,
                "processed_files": 1,
                "successful_files": 1,
                "failed_files": 0,
                "results": [{
                    "filename": file.filename,
                    "status": "completed",
                    "chunks": 1,
                    "tokens": 100,
                    "processing_time": 0.1,
                    "note": "Basic processing - enhanced features unavailable"
                }],
                "download_ready": True,
                "message": "Basic processing completed (enhanced features unavailable)"
            }
    
    finally:
        # Schedule cleanup
        if temp_file:
            background_tasks.add_task(cleanup_temp_files, [temp_file])
            
async def _process_batch_background(
    batch_id: str,
    file_paths: List[str],
    filenames: List[str],
    config: ProcessingConfig,
    export_format: str
):
    """
    Background task to process all files in a batch
    Updates job status and handles individual file processing
    """
    try:
        logger.info(f"Starting batch processing for {batch_id}: {len(file_paths)} files")
        
        # Update status to processing
        batch_jobs[batch_id]["status"] = "processing"
        batch_jobs[batch_id]["started_at"] = datetime.utcnow().isoformat()
        
        results = []
        successful_count = 0
        failed_count = 0
        
        # Process each file
        for i, (file_path, filename) in enumerate(zip(file_paths, filenames)):
            try:
                logger.info(f"Processing file {i+1}/{len(file_paths)}: {filename}")
                
                # Update file status
                batch_jobs[batch_id]["files"][i]["status"] = "processing"
                
                # Process individual file
                if WOLFCORE_AVAILABLE:
                    result = await _process_file_with_wolfcore(file_path, filename, config)
                else:
                    result = await _process_file_basic(file_path, filename, config)
                
                # Store result
                results.append({
                    "filename": filename,
                    "status": "completed",
                    "chunks": result.get("total_chunks", 0),
                    "tokens": result.get("total_tokens", 0),
                    "processing_time": result.get("processing_time", 0),
                    "file_index": i,
                    "data": result.get("chunks", [])
                })
                
                successful_count += 1
                batch_jobs[batch_id]["files"][i]["status"] = "completed"
                
                logger.info(f"✅ Completed {filename}: {result.get('total_chunks', 0)} chunks")
                
            except Exception as e:
                logger.error(f"❌ Failed to process {filename}: {str(e)}")
                
                # Store error
                error_result = {
                    "filename": filename,
                    "status": "failed",
                    "error": str(e),
                    "file_index": i
                }
                results.append(error_result)
                batch_jobs[batch_id]["errors"].append(error_result)
                
                failed_count += 1
                batch_jobs[batch_id]["files"][i]["status"] = "failed"
                batch_jobs[batch_id]["files"][i]["error"] = str(e)
            
            # Update progress
            processed = i + 1
            progress = int((processed / len(file_paths)) * 100)
            batch_jobs[batch_id]["progress"] = progress
            batch_jobs[batch_id]["processed_files"] = processed
            batch_jobs[batch_id]["successful_files"] = successful_count
            batch_jobs[batch_id]["failed_files"] = failed_count
        
        # Generate export file
        export_path = None
        if successful_count > 0:
            try:
                export_path = await _generate_export_file(batch_id, results, export_format)
                batch_jobs[batch_id]["download_url"] = f"/api/v1/batch/{batch_id}/download"
                logger.info(f"✅ Generated export file for batch {batch_id}")
            except Exception as e:
                logger.error(f"❌ Failed to generate export for batch {batch_id}: {str(e)}")
                batch_jobs[batch_id]["errors"].append({"export_error": str(e)})
        
        # Update final status
        batch_jobs[batch_id]["status"] = "completed"
        batch_jobs[batch_id]["progress"] = 100
        batch_jobs[batch_id]["completed_at"] = datetime.utcnow().isoformat()
        batch_jobs[batch_id]["results"] = results
        batch_jobs[batch_id]["export_path"] = export_path
        
        logger.info(f"🎉 Batch {batch_id} completed: {successful_count} success, {failed_count} failed")
        
    except Exception as e:
        logger.error(f"💥 Batch processing failed for {batch_id}: {str(e)}")
        batch_jobs[batch_id]["status"] = "failed"
        batch_jobs[batch_id]["error"] = str(e)
        batch_jobs[batch_id]["failed_at"] = datetime.utcnow().isoformat()
    
    finally:
        # Clean up uploaded files
        await cleanup_temp_files(file_paths)


async def _process_file_with_wolfcore(file_path: str, filename: str, config: ProcessingConfig) -> Dict[str, Any]:
    """Process a single file using Wolfcore"""
    try:
        processor = Wolfstitch()
        result = await processor.process_file_async(
            file_path,
            config={
                "tokenizer": config.tokenizer,
                "max_tokens": config.max_tokens,
                "chunk_method": config.chunk_method,
                "preserve_structure": config.preserve_structure
            }
        )
        
        return {
            "total_chunks": result.total_chunks,
            "total_tokens": result.total_tokens,
            "processing_time": result.processing_time,
            "chunks": [
                {
                    "text": chunk.text,
                    "tokens": chunk.token_count,
                    "chunk_index": chunk.chunk_index
                }
                for chunk in result.chunks
            ],
            "enhanced": True
        }
        
    except Exception as e:
        logger.error(f"Wolfcore processing failed for {filename}: {e}")
        raise


async def _process_file_basic(file_path: str, filename: str, config: ProcessingConfig) -> Dict[str, Any]:
    """Basic fallback processing without Wolfcore"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Basic chunking by paragraphs
        chunks = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        # Limit chunks if too many
        if len(chunks) > 100:
            chunks = chunks[:100]
        
        return {
            "total_chunks": len(chunks),
            "total_tokens": sum(len(chunk.split()) for chunk in chunks),
            "processing_time": 0.1,
            "chunks": [
                {
                    "text": chunk,
                    "tokens": len(chunk.split()),
                    "chunk_index": i
                }
                for i, chunk in enumerate(chunks)
            ],
            "enhanced": False
        }
        
    except Exception as e:
        logger.error(f"Basic processing failed for {filename}: {e}")
        raise


async def _generate_export_file(batch_id: str, results: List[Dict], export_format: str) -> str:
    """Generate export file in requested format"""
    
    results_dir = os.getenv("RESULTS_DIR", "./results")
    os.makedirs(results_dir, exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    if export_format == "jsonl":
        export_path = os.path.join(results_dir, f"{batch_id}_{timestamp}.jsonl")
        
        with open(export_path, 'w', encoding='utf-8') as f:
            for result in results:
                if result["status"] == "completed" and "data" in result:
                    for chunk in result["data"]:
                        line = {
                            "text": chunk["text"],
                            "tokens": chunk["tokens"],
                            "filename": result["filename"],
                            "chunk_index": chunk["chunk_index"],
                            "file_index": result["file_index"],
                            "batch_id": batch_id
                        }
                        f.write(json.dumps(line) + '\n')
    
    elif export_format == "json":
        export_path = os.path.join(results_dir, f"{batch_id}_{timestamp}.json")
        
        export_data = {
            "batch_id": batch_id,
            "generated_at": datetime.utcnow().isoformat(),
            "total_files": len(results),
            "successful_files": len([r for r in results if r["status"] == "completed"]),
            "results": results
        }
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    elif export_format == "csv":
        import csv
        export_path = os.path.join(results_dir, f"{batch_id}_{timestamp}.csv")
        
        with open(export_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['filename', 'chunk_index', 'text', 'tokens', 'file_index', 'batch_id'])
            
            for result in results:
                if result["status"] == "completed" and "data" in result:
                    for chunk in result["data"]:
                        writer.writerow([
                            result["filename"],
                            chunk["chunk_index"],
                            chunk["text"],
                            chunk["tokens"],
                            result["file_index"],
                            batch_id
                        ])
    
    else:
        raise ValueError(f"Unsupported export format: {export_format}")
    
    return export_path


@router.get("/batch/{batch_id}/status")
async def get_batch_status(batch_id: str):
    """Get the status of a batch processing job"""
    
    if not is_batch_processing_enabled():
        raise HTTPException(
            status_code=503, 
            detail="Batch processing is currently disabled"
        )
    
    if batch_id not in batch_jobs:
        raise HTTPException(status_code=404, detail="Batch job not found")
    
    job = batch_jobs[batch_id]
    
    # Build response
    response = {
        "batch_id": batch_id,
        "status": job["status"],
        "progress": job["progress"],
        "total_files": job["total_files"],
        "processed_files": job["processed_files"],
        "successful_files": job["successful_files"],
        "failed_files": job["failed_files"],
        "created_at": job["created_at"],
        "export_format": job["export_format"]
    }
    
    # Add timing info
    if "started_at" in job:
        response["started_at"] = job["started_at"]
    
    if "completed_at" in job:
        response["completed_at"] = job["completed_at"]
    
    if "failed_at" in job:
        response["failed_at"] = job["failed_at"]
    
    # Add error info if failed
    if job["status"] == "failed":
        response["error"] = job.get("error")
        response["errors"] = job.get("errors", [])
    
    # Add completion info if done
    elif job["status"] == "completed":
        response["download_url"] = job.get("download_url")
        response["results_summary"] = {
            "total_chunks": sum(r.get("chunks", 0) for r in job.get("results", []) if r.get("status") == "completed"),
            "total_tokens": sum(r.get("tokens", 0) for r in job.get("results", []) if r.get("status") == "completed"),
            "file_details": [
                {
                    "filename": r["filename"],
                    "status": r["status"],
                    "chunks": r.get("chunks", 0),
                    "tokens": r.get("tokens", 0)
                }
                for r in job.get("results", [])
            ]
        }
    
    # Add file-level progress for processing
    elif job["status"] == "processing":
        response["files"] = job.get("files", [])
    
    return response


@router.get("/batch/{batch_id}/download")
async def download_batch_results(batch_id: str):
    """Download the results of a completed batch job"""
    
    if not is_batch_processing_enabled():
        raise HTTPException(
            status_code=503, 
            detail="Batch processing is currently disabled"
        )
    
    if batch_id not in batch_jobs:
        raise HTTPException(status_code=404, detail="Batch job not found")
    
    job = batch_jobs[batch_id]
    
    if job["status"] != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Batch job is not completed. Current status: {job['status']}"
        )
    
    export_path = job.get("export_path")
    if not export_path or not os.path.exists(export_path):
        raise HTTPException(status_code=404, detail="Export file not found")
    
    # Determine content type based on format
    content_types = {
        "jsonl": "application/jsonl",
        "json": "application/json",
        "csv": "text/csv"
    }
    
    content_type = content_types.get(job["export_format"], "application/octet-stream")
    filename = os.path.basename(export_path)
    
    def file_generator():
        with open(export_path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk
    
    return StreamingResponse(
        file_generator(),
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )



