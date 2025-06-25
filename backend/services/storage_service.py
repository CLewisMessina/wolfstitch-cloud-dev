# backend/services/storage_service.py
"""
Wolfstitch Cloud - Storage Service
Manages file storage and provides secure download URLs
Environment-aware URL generation for dev/prod domains
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
        
        # Environment-aware base URL detection
        self.base_url = self._detect_base_url(base_url)
        
        # Create subdirectories
        self.exports_dir = self.storage_dir / "exports"
        self.temp_dir = self.storage_dir / "temp"
        self.exports_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        
        logger.info(f"Storage service initialized at: {self.storage_dir}")
        logger.info(f"Download base URL: {self.base_url}")
    
    def _detect_base_url(self, provided_url: str = "") -> str:
        """
        Intelligently detect the correct base URL for the current environment
        
        Priority order:
        1. Explicitly provided base_url parameter
        2. API_BASE_URL environment variable
        3. Auto-detection based on environment settings
        4. Railway-specific environment variables
        5. Fallback to localhost for development
        """
        if provided_url:
            return provided_url
        
        # Check explicit environment variable
        api_base_url = os.getenv("API_BASE_URL")
        if api_base_url:
            return api_base_url
        
        # Detect environment from ENVIRONMENT variable
        environment = os.getenv("ENVIRONMENT", "development").lower()
        
        # Production environment
        if environment == "production":
            return "https://api.wolfstitch.dev"
        
        # Development/staging environment
        elif environment in ["development", "staging", "dev"]:
            return "https://api-dev.wolfstitch.dev"
        
        # Check if we're on Railway (fallback detection)
        railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
        if railway_domain:
            return f"https://{railway_domain}"
        
        railway_url = os.getenv("RAILWAY_STATIC_URL")
        if railway_url:
            return railway_url
        
        # If we detect any Railway environment variables, assume development
        if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"):
            return "https://api-dev.wolfstitch.dev"
        
        # Local development fallback
        return "http://localhost:8000"
    
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
                "size_bytes": source_path.stat().st_size,
                "environment": os.getenv("ENVIRONMENT", "development"),
                "base_url_used": self.base_url
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
                json.dump(metadata, f, indent=2)
            
            logger.info(f"File stored successfully: {dest_filename}")
            logger.info(f"Generated download URL: {download_url}")
            logger.info(f"Environment: {metadata['environment']}, Base URL: {self.base_url}")
            
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
        
        # Generate the download URL
        download_url = f"{self.base_url}/api/v1/downloads/{storage_id}/{encoded_filename}"
        
        return download_url
    
    async def get_file_path(self, storage_id: str) -> Optional[Path]:
        """Get file path for a storage ID"""
        # Check metadata exists
        metadata_path = self.exports_dir / f"{storage_id}.json"
        if not metadata_path.exists():
            logger.warning(f"Metadata not found for storage_id: {storage_id}")
            return None
        
        # Find the actual file
        pattern = f"{storage_id}_*"
        matching_files = list(self.exports_dir.glob(pattern))
        
        if not matching_files:
            logger.warning(f"No files found matching pattern: {pattern}")
            return None
        
        # Return the first matching file (should be only one)
        file_path = matching_files[0]
        logger.debug(f"Found file for storage_id {storage_id}: {file_path}")
        return file_path
    
    async def validate_access(self, storage_id: str, user_id: Optional[str] = None) -> bool:
        """Validate access to a stored file"""
        try:
            # Check metadata exists
            metadata_path = self.exports_dir / f"{storage_id}.json"
            if not metadata_path.exists():
                logger.warning(f"Metadata file not found: {metadata_path}")
                return False
            
            # Load and check metadata
            import json
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Check expiration
            expires_at = datetime.fromisoformat(metadata["expires_at"])
            if datetime.utcnow() > expires_at:
                logger.info(f"File expired: {storage_id} (expired at {expires_at})")
                return False
            
            # Check if actual file exists
            file_path = await self.get_file_path(storage_id)
            if not file_path or not file_path.exists():
                logger.warning(f"Storage file missing for: {storage_id}")
                return False
            
            # Check user access (for future user-based access control)
            # For now, allow all access if file exists and not expired
            logger.debug(f"Access validated for storage_id: {storage_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating access for {storage_id}: {str(e)}")
            return False
    
    async def cleanup_old_exports(self):
        """Clean up expired export files"""
        try:
            current_time = datetime.utcnow()
            cleaned_count = 0
            
            for metadata_file in self.exports_dir.glob("*.json"):
                try:
                    import json
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    expires_at = datetime.fromisoformat(metadata["expires_at"])
                    if current_time > expires_at:
                        # Remove metadata file
                        metadata_file.unlink()
                        
                        # Remove actual export file
                        storage_id = metadata["storage_id"]
                        for export_file in self.exports_dir.glob(f"{storage_id}_*"):
                            export_file.unlink()
                            logger.debug(f"Removed expired file: {export_file}")
                            
                        cleaned_count += 1
                        logger.info(f"Cleaned up expired file: {storage_id}")
                        
                except Exception as e:
                    logger.error(f"Error cleaning up {metadata_file}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired files")
            else:
                logger.debug("No expired files to clean up")
                
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics for monitoring"""
        try:
            total_files = len(list(self.exports_dir.glob("*.json")))
            total_size = sum(f.stat().st_size for f in self.exports_dir.iterdir() if f.is_file())
            
            return {
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "storage_dir": str(self.storage_dir),
                "base_url": self.base_url,
                "environment": os.getenv("ENVIRONMENT", "development")
            }
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {"error": str(e)}


def _get_content_type(filename: str) -> str:
    """Get content type based on file extension"""
    extension = filename.lower().split('.')[-1]
    
    content_types = {
        'jsonl': 'application/jsonlines',
        'json': 'application/json',
        'csv': 'text/csv',
        'txt': 'text/plain',
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'md': 'text/markdown',
        'html': 'text/html',
        'xml': 'application/xml'
    }
    
    return content_types.get(extension, 'application/octet-stream')