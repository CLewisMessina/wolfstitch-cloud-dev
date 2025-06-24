# backend/services/result_storage.py
"""
Processing Result Storage Service
Stores complete processing results for later retrieval
"""

import json
import os
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import logging
import aiofiles
from pathlib import Path

logger = logging.getLogger(__name__)


class ResultStorageService:
    """
    Simple file-based storage for processing results
    In production, replace with Redis/Database storage
    """
    
    def __init__(self, storage_dir: str = "./processing_results"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self._cleanup_old_results()
    
    def _cleanup_old_results(self, max_age_hours: int = 24):
        """Remove results older than max_age_hours"""
        try:
            current_time = time.time()
            for file_path in self.storage_dir.glob("*.json"):
                file_age_hours = (current_time - file_path.stat().st_mtime) / 3600
                if file_age_hours > max_age_hours:
                    file_path.unlink()
                    logger.debug(f"Cleaned up old result: {file_path.name}")
        except Exception as e:
            logger.error(f"Error cleaning up old results: {e}")
    
    async def store_result(self, job_id: str, result_data: Dict[str, Any]) -> bool:
        """Store processing result"""
        try:
            file_path = self.storage_dir / f"{job_id}.json"
            
            # Add metadata
            result_data["stored_at"] = datetime.utcnow().isoformat()
            result_data["expires_at"] = (datetime.utcnow() + timedelta(hours=24)).isoformat()
            
            # Write to file asynchronously
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(result_data, indent=2))
            
            logger.info(f"Stored result for job_id: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store result for {job_id}: {e}")
            return False
    
    async def get_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve processing result"""
        try:
            file_path = self.storage_dir / f"{job_id}.json"
            
            if not file_path.exists():
                logger.warning(f"Result not found for job_id: {job_id}")
                return None
            
            # Check if expired
            file_age_hours = (time.time() - file_path.stat().st_mtime) / 3600
            if file_age_hours > 24:
                logger.warning(f"Result expired for job_id: {job_id}")
                file_path.unlink()
                return None
            
            # Read result
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                result = json.loads(content)
            
            logger.info(f"Retrieved result for job_id: {job_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to retrieve result for {job_id}: {e}")
            return None
    
    async def delete_result(self, job_id: str) -> bool:
        """Delete a stored result"""
        try:
            file_path = self.storage_dir / f"{job_id}.json"
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted result for job_id: {job_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete result for {job_id}: {e}")
            return False
    
    async def list_results(self, user_id: Optional[str] = None) -> list:
        """List all stored results (optionally filtered by user)"""
        results = []
        try:
            for file_path in self.storage_dir.glob("*.json"):
                try:
                    async with aiofiles.open(file_path, 'r') as f:
                        content = await f.read()
                        result = json.loads(content)
                        
                        # Basic metadata
                        results.append({
                            "job_id": file_path.stem,
                            "filename": result.get("filename", "Unknown"),
                            "stored_at": result.get("stored_at"),
                            "expires_at": result.get("expires_at"),
                            "total_chunks": result.get("total_chunks", 0),
                            "total_tokens": result.get("total_tokens", 0)
                        })
                except Exception as e:
                    logger.error(f"Error reading result file {file_path}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error listing results: {e}")
        
        return results


# Singleton instance
storage_service = ResultStorageService()