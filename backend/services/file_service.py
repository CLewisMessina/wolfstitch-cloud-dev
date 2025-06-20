"""
Wolfstitch Cloud - File Service
Handles file upload, storage, and validation
Week 1 implementation with local storage
"""

import os
import uuid
import aiofiles
from pathlib import Path
from datetime import datetime
from typing import Optional
import logging

from fastapi import UploadFile, HTTPException
from backend.models.schemas import FileInfo
from backend.config import settings

logger = logging.getLogger(__name__)


class FileService:
    """Service for handling file operations"""
    
    def __init__(self):
        # Ensure upload directory exists
        Path(settings.UPLOAD_DIR).mkdir(exist_ok=True)
        
        # In-memory file registry for Week 1
        self.files: dict = {}
    
    async def validate_upload(self, file: UploadFile, user) -> None:
        """Validate uploaded file"""
        
        # Check file size
        if hasattr(file, 'size') and file.size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB"
            )
        
        # Check file extension
        if file.filename:
            extension = Path(file.filename).suffix.lower().lstrip('.')
            if extension not in settings.ALLOWED_FILE_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"File type '{extension}' not supported"
                )
        else:
            raise HTTPException(status_code=400, detail="Filename is required")
    
    async def validate_anonymous_upload(self, file: UploadFile) -> None:
        """Validate anonymous upload with stricter limits"""
        
        # Anonymous uploads have smaller size limit
        max_anonymous_size = 10 * 1024 * 1024  # 10MB
        
        if hasattr(file, 'size') and file.size > max_anonymous_size:
            raise HTTPException(
                status_code=413,
                detail="Anonymous uploads limited to 10MB. Sign up for larger files."
            )
        
        # Same extension validation
        await self.validate_upload(file, None)
    
    async def save_upload(self, file: UploadFile, user_id: str) -> FileInfo:
        """Save uploaded file and return file info"""
        
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        
        # Determine file extension and format
        file_extension = Path(file.filename).suffix.lower()
        
        # Create safe filename
        safe_filename = f"{file_id}{file_extension}"
        file_path = Path(settings.UPLOAD_DIR) / safe_filename
        
        try:
            # Save file to disk
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            # Get file size
            file_size = len(content)
            
            # Detect format from extension
            format_name = self._detect_format(file.filename)
            
            # Create file info
            file_info = FileInfo(
                file_id=file_id,
                filename=file.filename,
                size_bytes=file_size,
                format=format_name,
                upload_time=datetime.utcnow(),
                processed=False,
                metadata={
                    "user_id": user_id,
                    "original_filename": file.filename,
                    "storage_path": str(file_path),
                    "content_type": file.content_type
                }
            )
            
            # Store in registry
            self.files[file_id] = file_info
            
            logger.info(f"File uploaded: {file_id} ({file.filename}, {file_size} bytes)")
            
            return file_info
            
        except Exception as e:
            # Cleanup file if save failed
            if file_path.exists():
                file_path.unlink()
            logger.error(f"File upload failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to save file")
    
    async def get_file_info(self, file_id: str, user_id: str) -> Optional[FileInfo]:
        """Get file information"""
        
        if file_id not in self.files:
            return None
        
        file_info = self.files[file_id]
        
        # Check ownership
        if file_info.metadata.get("user_id") != user_id:
            return None
        
        return file_info
    
    async def get_file_path(self, file_id: str, user_id: str) -> Optional[str]:
        """Get file path for processing"""
        
        file_info = await self.get_file_info(file_id, user_id)
        if not file_info:
            return None
        
        return file_info.metadata.get("storage_path")
    
    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete file"""
        
        file_info = await self.get_file_info(file_id, user_id)
        if not file_info:
            return False
        
        try:
            # Delete physical file
            file_path = Path(file_info.metadata["storage_path"])
            if file_path.exists():
                file_path.unlink()
            
            # Remove from registry
            del self.files[file_id]
            
            logger.info(f"File deleted: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"File deletion failed: {e}")
            return False
    
    async def analyze_file_background(self, file_id: str):
        """Analyze file in background (placeholder for Week 1)"""
        
        if file_id not in self.files:
            return
        
        try:
            file_info = self.files[file_id]
            
            # Use wolfcore to analyze file
            from wolfcore import FileParser
            
            parser = FileParser()
            file_path = file_info.metadata["storage_path"]
            
            parsed = parser.parse(file_path)
            
            # Update file info with analysis
            file_info.metadata.update({
                "word_count": parsed.word_count,
                "line_count": parsed.line_count,
                "encoding": parsed.encoding,
                "language": parsed.language,
                "analysis_completed": True
            })
            
            logger.info(f"File analysis completed: {file_id}")
            
        except Exception as e:
            logger.error(f"File analysis failed for {file_id}: {e}")
    
    def estimate_processing_time(self, file_info: FileInfo) -> int:
        """Estimate processing time in seconds"""
        
        # Simple estimation based on file size
        size_mb = file_info.size_bytes / (1024 * 1024)
        
        base_time = 10  # 10 seconds base
        size_factor = size_mb * 2  # 2 seconds per MB
        
        return int(base_time + size_factor)
    
    def _detect_format(self, filename: str) -> str:
        """Detect file format from filename"""
        
        extension = Path(filename).suffix.lower().lstrip('.')
        
        # Format mapping
        format_map = {
            'txt': 'txt',
            'pdf': 'pdf',
            'docx': 'docx',
            'doc': 'doc',
            'epub': 'epub',
            'html': 'html',
            'htm': 'html',
            'md': 'markdown',
            'markdown': 'markdown',
            'py': 'python',
            'js': 'javascript',
            'jsx': 'javascript',
            'ts': 'typescript',
            'tsx': 'typescript',
            'java': 'java',
            'cpp': 'cpp',
            'c': 'c',
            'h': 'c_header',
            'go': 'go',
            'rs': 'rust',
            'rb': 'ruby',
            'php': 'php',
            'json': 'json',
            'yaml': 'yaml',
            'yml': 'yaml',
            'csv': 'csv',
            'xlsx': 'xlsx'
        }
        
        return format_map.get(extension, 'unknown')
    
    async def list_user_files(
        self, 
        user_id: str, 
        limit: int = 20, 
        offset: int = 0
    ) -> list:
        """List user's uploaded files"""
        
        user_files = [
            file_info for file_info in self.files.values()
            if file_info.metadata.get("user_id") == user_id
        ]
        
        # Sort by upload time (newest first)
        user_files.sort(key=lambda x: x.upload_time, reverse=True)
        
        # Apply pagination
        return user_files[offset:offset + limit]
    
    async def get_storage_stats(self, user_id: str) -> dict:
        """Get storage statistics for user"""
        
        user_files = [
            file_info for file_info in self.files.values()
            if file_info.metadata.get("user_id") == user_id
        ]
        
        total_files = len(user_files)
        total_bytes = sum(f.size_bytes for f in user_files)
        
        return {
            "total_files": total_files,
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / (1024 * 1024), 2),
            "formats": self._get_format_breakdown(user_files)
        }
    
    def _get_format_breakdown(self, files: list) -> dict:
        """Get breakdown of files by format"""
        
        format_counts = {}
        for file_info in files:
            format_name = file_info.format
            format_counts[format_name] = format_counts.get(format_name, 0) + 1
        
        return format_counts