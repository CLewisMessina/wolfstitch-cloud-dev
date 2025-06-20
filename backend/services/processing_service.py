"""
Wolfstitch Cloud - Processing Service
Handles file processing, job management, and status tracking
Week 1 implementation with basic functionality
"""

import uuid
import asyncio
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

from backend.models.schemas import (
    ProcessingConfig, ProcessingResult, ProcessingStatus, 
    ChunkData, ExportResponse
)

logger = logging.getLogger(__name__)


class ProcessingService:
    """Service for handling file processing operations"""
    
    def __init__(self):
        # In-memory storage for Week 1 (will be replaced with Redis/DB in Week 2)
        self.jobs: Dict[str, Dict] = {}
        self.results: Dict[str, ProcessingResult] = {}
        self.anonymous_results: Dict[str, Dict] = {}
    
    async def process_file_background(
        self,
        job_id: str,
        file_id: str,
        user_id: str,
        config: ProcessingConfig,
        export_format: str,
        webhook_url: Optional[str] = None
    ):
        """Process file in background"""
        try:
            logger.info(f"Starting background processing for job {job_id}")
            
            # Update job status to processing
            await self.update_job_status(job_id, "processing", 10.0, "Starting processing...")
            
            # For Week 1, simulate processing with wolfcore
            from wolfcore import Wolfstitch
            
            # Get file path from file_id (mock implementation)
            file_path = f"uploads/{file_id}"  # Simplified for Week 1
            
            if not os.path.exists(file_path):
                raise Exception(f"File not found: {file_path}")
            
            # Process with wolfcore
            await self.update_job_status(job_id, "processing", 30.0, "Parsing file...")
            
            wf = Wolfstitch()
            result = await wf.process_file_async(
                file_path=file_path,
                tokenizer=config.tokenizer,
                max_tokens=config.max_tokens,
                format=export_format
            )
            
            await self.update_job_status(job_id, "processing", 80.0, "Finalizing results...")
            
            # Store result
            processing_result = ProcessingResult(
                job_id=job_id,
                file_id=file_id,
                filename=os.path.basename(file_path),
                status="completed",
                chunks=[
                    ChunkData(
                        id=i,
                        text=chunk.text,
                        token_count=chunk.token_count,
                        start_position=chunk.start_position,
                        end_position=chunk.end_position,
                        metadata=chunk.metadata
                    ) for i, chunk in enumerate(result.chunks)
                ],
                total_chunks=len(result.chunks),
                total_tokens=result.total_tokens,
                avg_tokens_per_chunk=result.avg_tokens_per_chunk,
                processing_time=result.processing_time,
                config=config,
                export_format=export_format,
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            
            self.results[job_id] = processing_result
            
            # Final status update
            await self.update_job_status(job_id, "completed", 100.0, "Processing completed")
            
            logger.info(f"Processing completed for job {job_id}")
            
        except Exception as e:
            logger.error(f"Processing failed for job {job_id}: {e}")
            await self.update_job_status(job_id, "failed", 0.0, str(e))
    
    async def create_job_status(
        self,
        job_id: str,
        file_id: str,
        user_id: str,
        config: ProcessingConfig
    ):
        """Create initial job status"""
        self.jobs[job_id] = {
            "job_id": job_id,
            "file_id": file_id,
            "user_id": user_id,
            "status": "pending",
            "progress": 0.0,
            "current_step": "Queued for processing",
            "chunks_processed": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "config": config
        }
    
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        progress: float,
        current_step: str
    ):
        """Update job status"""
        if job_id in self.jobs:
            self.jobs[job_id].update({
                "status": status,
                "progress": progress,
                "current_step": current_step,
                "updated_at": datetime.utcnow()
            })
    
    async def get_job_status(self, job_id: str, user_id: str) -> Optional[ProcessingStatus]:
        """Get job status"""
        if job_id not in self.jobs:
            return None
        
        job_data = self.jobs[job_id]
        
        # Check ownership (simplified for Week 1)
        if job_data["user_id"] != user_id:
            return None
        
        return ProcessingStatus(
            job_id=job_id,
            status=job_data["status"],
            progress=job_data["progress"],
            current_step=job_data["current_step"],
            chunks_processed=job_data["chunks_processed"],
            created_at=job_data["created_at"],
            updated_at=job_data["updated_at"]
        )
    
    async def get_job_result(
        self, 
        job_id: str, 
        user_id: str,
        include_chunks: bool = True,
        chunk_limit: Optional[int] = None
    ) -> Optional[ProcessingResult]:
        """Get job result"""
        if job_id not in self.results:
            return None
        
        result = self.results[job_id]
        
        # Apply chunk limit if specified
        if chunk_limit and include_chunks:
            result.chunks = result.chunks[:chunk_limit]
        
        return result
    
    async def cancel_job(self, job_id: str, user_id: str) -> bool:
        """Cancel a job"""
        if job_id not in self.jobs:
            return False
        
        job_data = self.jobs[job_id]
        
        if job_data["user_id"] != user_id:
            return False
        
        if job_data["status"] in ["completed", "failed", "cancelled"]:
            return False
        
        # Cancel the job
        await self.update_job_status(job_id, "cancelled", 0.0, "Cancelled by user")
        return True
    
    async def list_user_jobs(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[Dict]:
        """List user's jobs"""
        user_jobs = [
            job for job in self.jobs.values() 
            if job["user_id"] == user_id
        ]
        
        if status_filter:
            user_jobs = [job for job in user_jobs if job["status"] == status_filter]
        
        # Sort by creation time (newest first)
        user_jobs.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Apply pagination
        return user_jobs[offset:offset + limit]
    
    async def get_job_analytics(self, job_id: str, user_id: str) -> Optional[Dict]:
        """Get job analytics (premium feature)"""
        if job_id not in self.results:
            return None
        
        result = self.results[job_id]
        
        # Generate analytics
        return {
            "job_id": job_id,
            "total_chunks": result.total_chunks,
            "total_tokens": result.total_tokens,
            "avg_tokens_per_chunk": result.avg_tokens_per_chunk,
            "processing_time": result.processing_time,
            "token_distribution": self._calculate_token_distribution(result.chunks),
            "chunk_quality_metrics": self._calculate_chunk_quality(result.chunks)
        }
    
    def _calculate_token_distribution(self, chunks: List[ChunkData]) -> Dict[str, int]:
        """Calculate token distribution across chunks"""
        distribution = {
            "0-100": 0,
            "100-500": 0,
            "500-1000": 0,
            "1000+": 0
        }
        
        for chunk in chunks:
            token_count = chunk.token_count
            if token_count <= 100:
                distribution["0-100"] += 1
            elif token_count <= 500:
                distribution["100-500"] += 1
            elif token_count <= 1000:
                distribution["500-1000"] += 1
            else:
                distribution["1000+"] += 1
        
        return distribution
    
    def _calculate_chunk_quality(self, chunks: List[ChunkData]) -> Dict[str, float]:
        """Calculate chunk quality metrics"""
        if not chunks:
            return {}
        
        lengths = [len(chunk.text) for chunk in chunks]
        token_counts = [chunk.token_count for chunk in chunks]
        
        return {
            "avg_length": sum(lengths) / len(lengths),
            "length_variance": sum((l - sum(lengths) / len(lengths)) ** 2 for l in lengths) / len(lengths),
            "avg_token_density": sum(token_counts) / sum(lengths) if sum(lengths) > 0 else 0,
            "consistency_score": 1.0 - (max(token_counts) - min(token_counts)) / max(token_counts) if max(token_counts) > 0 else 0
        }
    
    async def export_result(
        self,
        job_id: str,
        user_id: str,
        format: str,
        include_metadata: bool = True,
        chunk_range: Optional[Dict[str, int]] = None,
        custom_fields: Optional[List[str]] = None
    ) -> ExportResponse:
        """Export processing result"""
        export_id = str(uuid.uuid4())
        
        # For Week 1, return mock export response
        return ExportResponse(
            export_id=export_id,
            job_id=job_id,
            format=format,
            download_url=f"/api/v1/processing/download/{export_id}",
            expires_at=datetime.utcnow() + timedelta(hours=24),
            size_bytes=1024,  # Mock size
            created_at=datetime.utcnow()
        )
    
    async def get_export_info(self, export_id: str, user_id: str) -> Optional[ExportResponse]:
        """Get export information"""
        # Mock implementation for Week 1
        return None
    
    async def get_export_file_path(self, export_id: str) -> str:
        """Get file path for export"""
        # Mock implementation for Week 1
        return f"exports/{export_id}.jsonl"
    
    async def store_anonymous_result(
        self,
        download_id: str,
        result: Any,
        expiry_hours: int = 1
    ):
        """Store anonymous processing result"""
        self.anonymous_results[download_id] = {
            "result": result,
            "expires_at": datetime.utcnow() + timedelta(hours=expiry_hours)
        }
    
    async def get_anonymous_result(self, download_id: str) -> Optional[Any]:
        """Get anonymous result"""
        if download_id not in self.anonymous_results:
            return None
        
        data = self.anonymous_results[download_id]
        
        if datetime.utcnow() > data["expires_at"]:
            del self.anonymous_results[download_id]
            return None
        
        return data["result"]
    
    async def export_anonymous_result(self, result: Any) -> str:
        """Export anonymous result to temporary file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            # Mock export for Week 1
            f.write('{"text": "Sample chunk", "tokens": 10}\n')
            return f.name
    
    async def get_user_tokenizers(self, user) -> List[str]:
        """Get available tokenizers for user"""
        base_tokenizers = ["word-estimate"]
        
        if user.has_premium_features:
            from wolfcore import get_supported_tokenizers
            try:
                return get_supported_tokenizers()
            except:
                pass
        
        return base_tokenizers
    
    def estimate_completion_time(self, file_info, config: ProcessingConfig) -> datetime:
        """Estimate completion time"""
        # Simple estimation for Week 1
        base_time = 30  # 30 seconds base
        size_factor = getattr(file_info, 'size_bytes', 1024) / 1024 / 1024  # MB
        return datetime.utcnow() + timedelta(seconds=base_time + size_factor * 10)