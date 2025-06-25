# backend/services/storage_service.py
"""
Wolfstitch Cloud - Storage Service
Manages file storage and provides secure download URLs
"""

import os
import uuid
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing file storage and downloads"""
    
    def __init__(self, storage_dir: str = "./storage", base_url: str = ""):
        """
        Initialize storage service
        
        Args:
            storage_dir: Directory for file storage
            base_url: Base URL for generating download links
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost:8000")
        
        # Create subdirectories
        self.exports_dir = self.storage_dir / "exports"
        self.temp_dir = self.storage_dir / "temp"
        self.exports_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        
        logger.info(f"Storage service initialized at: {self.storage_dir}")
    
    async def store_export_file(
        self,
        source_path: Path,
        job_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Store an export file and generate download information
        
        Args:
            source_path: Path to the generated export file
            job_id: Job identifier
            user_id: Optional user identifier for access control
            
        Returns:
            Dict with storage information and download URL
        """
        try:
            # Generate unique storage ID
            storage_id = f"{job_id}_{uuid.uuid4().hex[:8]}"
            
            # Create storage metadata
            metadata = {
                "storage_id": storage_id,
                "job_id": job_id,
                "user_id": user_id,
                "original_filename": source_path.name,
                "stored_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
                "size_bytes": source_path.stat().st_size
            }
            
            # Copy file to storage location
            dest_filename = f"{storage_id}_{source_path.name}"
            dest_path = self.exports_dir / dest_filename
            shutil.copy2(source_path, dest_path)
            
            # Generate download URL
            download_url = self._generate_download_url(storage_id, dest_filename)
            
            # Store metadata
            metadata_path = self.exports_dir / f"{storage_id}.json"
            import json
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            logger.info(f"File stored successfully: {dest_filename}")
            
            return {
                "storage_id": storage_id,
                "download_url": download_url,
                "filename": source_path.name,
                "size_bytes": metadata["size_bytes"],
                "expires_at": metadata["expires_at"]
            }
            
        except Exception as e:
            logger.error(f"Error storing export file: {str(e)}")
            raise
    
    def _generate_download_url(self, storage_id: str, filename: str) -> str:
        """Generate secure download URL"""
        # URL-encode the filename to handle special characters
        encoded_filename = quote(filename)
        
        # For development, use direct download endpoint
        # In production, this would use signed URLs with S3 or similar
        return f"{self.base_url}/api/v1/downloads/{storage_id}/{encoded_filename}"
    
    async def get_file_path(self, storage_id: str) -> Optional[Path]:
        """Get file path for a storage ID"""
        # Check metadata exists
        metadata_path = self.exports_dir / f"{storage_id}.json"
        if not metadata_path.exists():
            return None
        
        # Load metadata
        import json
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Check if expired
        expires_at = datetime.fromisoformat(metadata["expires_at"])
        if datetime.utcnow() > expires_at:
            logger.warning(f"File expired: {storage_id}")
            return None
        
        # Find the actual file
        pattern = f"{storage_id}_*"
        files = list(self.exports_dir.glob(pattern))
        
        if files:
            return files[0]
        
        return None
    
    async def validate_access(
        self,
        storage_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Validate access to a stored file
        
        Args:
            storage_id: Storage identifier
            user_id: User requesting access
            
        Returns:
            True if access is allowed
        """
        # Load metadata
        metadata_path = self.exports_dir / f"{storage_id}.json"
        if not metadata_path.exists():
            return False
        
        import json
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Check expiration
        expires_at = datetime.fromisoformat(metadata["expires_at"])
        if datetime.utcnow() > expires_at:
            return False
        
        # Check user access (if user_id is stored)
        if metadata.get("user_id") and user_id:
            return metadata["user_id"] == user_id
        
        # Allow access for files without user restrictions
        return True
    
    async def cleanup_expired_files(self):
        """Clean up expired files from storage"""
        try:
            current_time = datetime.utcnow()
            cleaned_count = 0
            
            # Check all metadata files
            for metadata_path in self.exports_dir.glob("*.json"):
                try:
                    import json
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    
                    # Check if expired
                    expires_at = datetime.fromisoformat(metadata["expires_at"])
                    if current_time > expires_at:
                        storage_id = metadata["storage_id"]
                        
                        # Remove the actual file
                        pattern = f"{storage_id}_*"
                        for file_path in self.exports_dir.glob(pattern):
                            file_path.unlink()
                            logger.debug(f"Removed expired file: {file_path.name}")
                        
                        # Remove metadata
                        metadata_path.unlink()
                        cleaned_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing metadata file {metadata_path}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired files")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        total_size = 0
        file_count = 0
        
        for file_path in self.exports_dir.glob("*"):
            if file_path.suffix != ".json":
                total_size += file_path.stat().st_size
                file_count += 1
        
        return {
            "total_files": file_count,
            "total_size_bytes": total_size,
            "total_size_readable": self._format_file_size(total_size),
            "storage_path": str(self.storage_dir)
        }
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"