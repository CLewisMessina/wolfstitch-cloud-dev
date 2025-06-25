# backend/api/downloads.py
"""
Wolfstitch Cloud - Downloads API
Serves generated export files for download
"""

import os
from pathlib import Path
from typing import Optional
import logging

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import FileResponse, StreamingResponse
from backend.services.storage_service import StorageService
from backend.dependencies import get_current_user, get_rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize storage service
storage_service = StorageService()


@router.get("/{storage_id}/{filename}")
async def download_file(
    storage_id: str,
    filename: str,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    rate_limiter=None  # Optional rate limiter dependency
):
    """
    Download a generated export file
    
    Args:
        storage_id: Unique storage identifier
        filename: Original filename (for proper download naming)
        user_id: Optional user ID for access control
    """
    try:
        # Validate access
        if not await storage_service.validate_access(storage_id, user_id):
            logger.warning(f"Access denied for storage_id: {storage_id}, user: {user_id}")
            raise HTTPException(
                status_code=403,
                detail="Access denied or file expired"
            )
        
        # Get file path
        file_path = await storage_service.get_file_path(storage_id)
        if not file_path or not file_path.exists():
            logger.error(f"File not found for storage_id: {storage_id}")
            raise HTTPException(
                status_code=404,
                detail="File not found or has been removed"
            )
        
        # Determine content type based on file extension
        content_type = _get_content_type(filename)
        
        logger.info(f"Serving download: {filename} (storage_id: {storage_id})")
        
        # Return file response with proper headers
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving download: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error processing download request"
        )


@router.get("/{storage_id}/{filename}/stream")
async def stream_download(
    storage_id: str,
    filename: str,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    range: Optional[str] = Header(None)
):
    """
    Stream download with support for partial content (resume)
    
    Args:
        storage_id: Unique storage identifier
        filename: Original filename
        user_id: Optional user ID for access control
        range: HTTP Range header for partial downloads
    """
    try:
        # Validate access
        if not await storage_service.validate_access(storage_id, user_id):
            raise HTTPException(
                status_code=403,
                detail="Access denied or file expired"
            )
        
        # Get file path
        file_path = await storage_service.get_file_path(storage_id)
        if not file_path or not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail="File not found"
            )
        
        file_size = file_path.stat().st_size
        
        # Handle range requests for resume support
        if range:
            return await _handle_range_request(file_path, filename, file_size, range)
        
        # Stream entire file
        async def iterfile():
            async with aiofiles.open(file_path, 'rb') as f:
                while chunk := await f.read(1024 * 1024):  # 1MB chunks
                    yield chunk
        
        return StreamingResponse(
            iterfile(),
            media_type=_get_content_type(filename),
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming download: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error processing download request"
        )


async def _handle_range_request(file_path: Path, filename: str, file_size: int, range_header: str):
    """Handle HTTP range requests for partial downloads"""
    try:
        import aiofiles
        
        # Parse range header (e.g., "bytes=0-1023")
        range_spec = range_header.replace("bytes=", "")
        ranges = range_spec.split("-")
        
        start = int(ranges[0]) if ranges[0] else 0
        end = int(ranges[1]) if ranges[1] else file_size - 1
        
        # Validate range
        if start >= file_size or end >= file_size:
            raise HTTPException(
                status_code=416,
                detail="Requested range not satisfiable"
            )
        
        # Calculate content length
        content_length = end - start + 1
        
        # Stream partial content
        async def iterfile_range():
            async with aiofiles.open(file_path, 'rb') as f:
                await f.seek(start)
                remaining = content_length
                
                while remaining > 0:
                    chunk_size = min(1024 * 1024, remaining)  # 1MB chunks
                    chunk = await f.read(chunk_size)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        
        return StreamingResponse(
            iterfile_range(),
            status_code=206,  # Partial Content
            media_type=_get_content_type(filename),
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(content_length),
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes"
            }
        )
        
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid range header"
        )


def _get_content_type(filename: str) -> str:
    """Determine content type based on file extension"""
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    content_types = {
        'jsonl': 'application/jsonl',
        'json': 'application/json',
        'csv': 'text/csv',
        'txt': 'text/plain',
        'xml': 'application/xml',
        'pdf': 'application/pdf',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'xls': 'application/vnd.ms-excel'
    }
    
    return content_types.get(ext, 'application/octet-stream')


# Import aiofiles for async file operations
try:
    import aiofiles
except ImportError:
    logger.warning("aiofiles not installed - falling back to sync file operations")
    aiofiles = None