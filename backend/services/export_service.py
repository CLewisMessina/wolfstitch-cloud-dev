# backend/services/export_service.py
"""
Wolfstitch Cloud - Export Service
Generates complete export files in various formats (JSONL, JSON, CSV)
"""

import json
import csv
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ExportService:
    """Service for generating export files from processed data"""
    
    def __init__(self, export_dir: str = "./exports"):
        """
        Initialize export service
        
        Args:
            export_dir: Directory to store generated export files
        """
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(exist_ok=True)
        logger.info(f"Export service initialized with directory: {self.export_dir}")
    
    async def generate_export(
        self,
        job_id: str,
        processing_result: Dict[str, Any],
        export_format: str = "jsonl"
    ) -> Dict[str, Any]:
        """
        Generate export file from processing results
        
        Args:
            job_id: Unique job identifier
            processing_result: Complete processing results with all chunks
            export_format: Format for export (jsonl, json, csv)
            
        Returns:
            Dict containing export file information
        """
        try:
            logger.info(f"Generating {export_format} export for job {job_id}")
            
            # Generate filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            base_filename = processing_result.get("filename", "export").replace(".", "_")
            filename = f"{base_filename}_{timestamp}_{job_id[:8]}.{export_format}"
            file_path = self.export_dir / filename
            
            # Generate export based on format
            if export_format == "jsonl":
                await self._generate_jsonl(file_path, processing_result)
            elif export_format == "json":
                await self._generate_json(file_path, processing_result)
            elif export_format == "csv":
                await self._generate_csv(file_path, processing_result)
            else:
                raise ValueError(f"Unsupported export format: {export_format}")
            
            # Calculate file size
            file_size = file_path.stat().st_size
            
            # Return export information
            export_info = {
                "filename": filename,
                "file_path": str(file_path),
                "format": export_format,
                "size_bytes": file_size,
                "size_readable": self._format_file_size(file_size),
                "created_at": datetime.utcnow().isoformat(),
                "chunks_count": processing_result.get("total_chunks", 0),
                "tokens_count": processing_result.get("total_tokens", 0)
            }
            
            logger.info(f"Export generated successfully: {filename} ({export_info['size_readable']})")
            return export_info
            
        except Exception as e:
            logger.error(f"Error generating export for job {job_id}: {str(e)}")
            raise
    
    async def _generate_jsonl(self, file_path: Path, processing_result: Dict[str, Any]):
        """Generate JSONL export with complete chunks"""
        with open(file_path, 'w', encoding='utf-8') as f:
            # Write metadata as first line
            metadata = {
                "_metadata": {
                    "filename": processing_result.get("filename"),
                    "job_id": processing_result.get("metadata", {}).get("job_id"),
                    "processed_at": processing_result.get("metadata", {}).get("processed_at"),
                    "total_chunks": processing_result.get("total_chunks"),
                    "total_tokens": processing_result.get("total_tokens"),
                    "chunk_method": processing_result.get("chunks", [{}])[0].get("metadata", {}).get("chunk_method"),
                    "tokenizer": processing_result.get("chunks", [{}])[0].get("metadata", {}).get("tokenizer")
                }
            }
            f.write(json.dumps(metadata, ensure_ascii=False) + '\n')
            
            # Write each chunk as a separate JSON line
            for chunk in processing_result.get("chunks", []):
                chunk_data = {
                    "chunk_id": chunk.get("chunk_id"),
                    "text": chunk.get("text"),  # FULL TEXT - NO TRUNCATION
                    "tokens": chunk.get("tokens"),
                    "start_pos": chunk.get("start_pos"),
                    "end_pos": chunk.get("end_pos"),
                    "metadata": chunk.get("metadata", {})
                }
                f.write(json.dumps(chunk_data, ensure_ascii=False) + '\n')
    
    async def _generate_json(self, file_path: Path, processing_result: Dict[str, Any]):
        """Generate JSON export with complete chunks"""
        export_data = {
            "metadata": {
                "filename": processing_result.get("filename"),
                "job_id": processing_result.get("metadata", {}).get("job_id"),
                "processed_at": processing_result.get("metadata", {}).get("processed_at"),
                "total_chunks": processing_result.get("total_chunks"),
                "total_tokens": processing_result.get("total_tokens"),
                "export_format": "json"
            },
            "chunks": []
        }
        
        # Add all chunks with full content
        for chunk in processing_result.get("chunks", []):
            export_data["chunks"].append({
                "chunk_id": chunk.get("chunk_id"),
                "text": chunk.get("text"),  # FULL TEXT - NO TRUNCATION
                "tokens": chunk.get("tokens"),
                "start_pos": chunk.get("start_pos"),
                "end_pos": chunk.get("end_pos"),
                "metadata": chunk.get("metadata", {})
            })
        
        # Write formatted JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    async def _generate_csv(self, file_path: Path, processing_result: Dict[str, Any]):
        """Generate CSV export with complete chunks"""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                "chunk_id",
                "text",
                "tokens",
                "start_pos",
                "end_pos",
                "chunk_method",
                "tokenizer",
                "filename"
            ])
            
            # Write each chunk
            for chunk in processing_result.get("chunks", []):
                writer.writerow([
                    chunk.get("chunk_id"),
                    chunk.get("text"),  # FULL TEXT - NO TRUNCATION
                    chunk.get("tokens"),
                    chunk.get("start_pos", ""),
                    chunk.get("end_pos", ""),
                    chunk.get("metadata", {}).get("chunk_method", ""),
                    chunk.get("metadata", {}).get("tokenizer", ""),
                    processing_result.get("filename", "")
                ])
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    async def cleanup_old_exports(self, max_age_hours: int = 24):
        """Clean up export files older than specified hours"""
        try:
            current_time = datetime.utcnow()
            cleaned_count = 0
            
            for file_path in self.export_dir.glob("*"):
                if file_path.is_file():
                    # Check file age
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    age_hours = (current_time - file_time).total_seconds() / 3600
                    
                    if age_hours > max_age_hours:
                        file_path.unlink()
                        cleaned_count += 1
                        logger.debug(f"Cleaned up old export: {file_path.name}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old export files")
                
        except Exception as e:
            logger.error(f"Error cleaning up old exports: {str(e)}")
    
    def get_export_path(self, filename: str) -> Optional[Path]:
        """Get full path for an export file if it exists"""
        file_path = self.export_dir / filename
        return file_path if file_path.exists() else None