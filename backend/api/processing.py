"""
Wolfstitch Cloud - Processing API Routes
Clean final version with proper variable definitions
"""

import asyncio
import logging
import tempfile
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends

from backend.dependencies import get_current_user, get_rate_limiter

# Import enhanced wolfcore modules
try:
    from wolfcore import Wolfstitch, ProcessingConfig as WolfcoreProcessingConfig
    from wolfcore.exceptions import ProcessingError, ParsingError
    from wolfcore.cleaner import clean_text_async
    from wolfcore.chunker import chunk_text_async, ChunkingConfig
    ENHANCED_MODULES_AVAILABLE = True
    logging.info("Enhanced wolfcore modules loaded successfully")
except ImportError as e:
    logging.warning(f"Enhanced modules not available: {e}")
    ENHANCED_MODULES_AVAILABLE = False

# Global availability flags
AUTH_AVAILABLE = True
RATE_LIMITER_AVAILABLE = True
SCHEMAS_AVAILABLE = True

logger = logging.getLogger(__name__)
router = APIRouter()

# =============================================================================
# SYSTEM ENDPOINTS (No Auth Required)
# =============================================================================

@router.get("/loading-status")
async def get_loading_status():
    """Get progressive loading status of premium features"""
    try:
        if ENHANCED_MODULES_AVAILABLE:
            from wolfcore import get_loading_status
            status = get_loading_status()
            return status
        else:
            return {
                "basic_features": True,
                "premium_features": False,
                "enhanced_modules": False,
                "message": "Enhanced modules not available"
            }
    except Exception as e:
        logger.error(f"Error getting loading status: {e}")
        return {"error": str(e)}


@router.get("/tokenizers")
async def get_available_tokenizers():
    """Get list of available tokenizers"""
    try:
        if ENHANCED_MODULES_AVAILABLE:
            from wolfcore import get_supported_tokenizers
            return get_supported_tokenizers()
        else:
            return ["word-estimate"]
    except Exception as e:
        logger.error(f"Error getting tokenizers: {e}")
        return ["word-estimate"]


# =============================================================================
# QUICK PROCESSING (No Auth Required)
# =============================================================================

@router.post("/quick-process")
async def quick_process_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tokenizer: str = Form("word-estimate"),
    max_tokens: int = Form(1024),
    chunk_method: str = Form("paragraph")
):
    """
    Process file immediately without authentication
    Enhanced version with graceful fallbacks
    """
    temp_file = None
    
    try:
        logger.info(f"Quick processing file: {file.filename}")
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_file = tmp.name
        
        if ENHANCED_MODULES_AVAILABLE:
            # Use enhanced processing
            try:
                config = WolfcoreProcessingConfig(
                    chunk_method=chunk_method,
                    max_tokens=max_tokens,
                    tokenizer=tokenizer
                )
                
                processor = Wolfstitch(config)
                result = await processor.process_file_async(temp_file)
                
                # Convert to simple dict response
                response_data = {
                    "job_id": f"quick-{hash(file.filename)}",
                    "total_chunks": result.total_chunks,
                    "total_tokens": result.total_tokens,
                    "processing_time": result.processing_time,
                    "status": "completed",
                    "enhanced": True,
                    "chunks": [
                        {
                            "text": chunk.text,
                            "token_count": chunk.token_count,
                            "chunk_index": chunk.chunk_index
                        }
                        for chunk in result.chunks[:5]  # First 5 chunks for preview
                    ],
                    "file_info": result.file_info,
                    "metadata": result.metadata
                }
                
            except Exception as enhanced_error:
                logger.warning(f"Enhanced processing failed: {enhanced_error}, falling back to basic")
                response_data = await _basic_processing_fallback(temp_file, file.filename)
        else:
            # Use basic processing
            response_data = await _basic_processing_fallback(temp_file, file.filename)
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_temp_file, temp_file)
        
        logger.info(f"Processing completed: {response_data['total_chunks']} chunks")
        return response_data
        
    except Exception as e:
        logger.error(f"Processing error: {e}")
        if temp_file:
            background_tasks.add_task(cleanup_temp_file, temp_file)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


async def _basic_processing_fallback(temp_file: str, filename: str):
    """Fallback to basic processing if enhanced modules fail"""
    try:
        from wolfcore.parsers import FileParser
        
        parser = FileParser()
        parsed_file = parser.parse(temp_file)
        
        # Basic paragraph chunking
        chunks_text = [p.strip() for p in parsed_file.text.split("\n\n") if p.strip()]
        if not chunks_text:
            chunks_text = [parsed_file.text]
        
        total_tokens = sum(len(chunk.split()) * 1.3 for chunk in chunks_text)
        
        return {
            "job_id": f"basic-{hash(filename)}",
            "total_chunks": len(chunks_text),
            "total_tokens": int(total_tokens),
            "processing_time": 1.0,
            "status": "completed",
            "enhanced": False,
            "chunks": [
                {
                    "text": chunk,
                    "token_count": int(len(chunk.split()) * 1.3),
                    "chunk_index": i
                }
                for i, chunk in enumerate(chunks_text[:5])
            ],
            "file_info": {
                "filename": parsed_file.filename,
                "format": parsed_file.format,
                "size_bytes": parsed_file.size_bytes
            },
            "metadata": {"processing_type": "basic_fallback"}
        }
    except Exception as e:
        logger.error(f"Even basic processing failed: {e}")
        raise


# =============================================================================
# TESTING ENDPOINTS (Development Only)
# =============================================================================

@router.post("/test-enhanced")
async def test_enhanced_modules():
    """Test if enhanced modules are working"""
    result = {
        "enhanced_modules_available": ENHANCED_MODULES_AVAILABLE,
        "schemas_available": SCHEMAS_AVAILABLE,
        "auth_available": AUTH_AVAILABLE,
        "rate_limiter_available": RATE_LIMITER_AVAILABLE
    }
    
    if ENHANCED_MODULES_AVAILABLE:
        try:
            # Quick test of each module
            from wolfcore.cleaner import clean_text
            from wolfcore.chunker import split_text
            from wolfcore import Wolfstitch
            
            # Test cleaner
            cleaned = clean_text("Test   text", file_extension=".txt")
            result["cleaner_test"] = "PASS" if "Test text" in cleaned else "FAIL"
            
            # Test chunker
            chunks = split_text("Para 1\n\nPara 2", method="paragraph")
            result["chunker_test"] = "PASS" if len(chunks) == 2 else "FAIL"
            
            # Test processor
            processor = Wolfstitch()
            tokenizers = processor.get_available_tokenizers()
            result["processor_test"] = "PASS" if len(tokenizers) > 0 else "FAIL"
            
        except Exception as e:
            result["test_error"] = str(e)
    
    return result


@router.post("/test-cleaner")
async def test_text_cleaner(
    text: str = Form("Test   text   with   spaces"),
    file_extension: str = Form(".txt")
):
    """Test the enhanced text cleaner"""
    try:
        if ENHANCED_MODULES_AVAILABLE:
            cleaned = await clean_text_async(text, file_extension=file_extension)
            return {
                "original": text,
                "cleaned": cleaned,
                "enhanced": True,
                "original_length": len(text),
                "cleaned_length": len(cleaned)
            }
        else:
            return {
                "original": text,
                "cleaned": text.strip(),
                "enhanced": False,
                "message": "Enhanced modules not available"
            }
    except Exception as e:
        return {"error": str(e)}


@router.post("/test-chunker")
async def test_text_chunker(
    text: str = Form("First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph here."),
    chunk_method: str = Form("paragraph"),
    max_tokens: int = Form(50)
):
    """Test the enhanced text chunker"""
    try:
        if ENHANCED_MODULES_AVAILABLE:
            config = ChunkingConfig(
                method=chunk_method,
                max_tokens=max_tokens,
                overlap_tokens=0
            )
            
            chunks = await chunk_text_async(text, config)
            
            return {
                "original_text": text,
                "original_length": len(text),
                "total_chunks": len(chunks),
                "chunk_method": chunk_method,
                "max_tokens": max_tokens,
                "enhanced": True,
                "chunks_preview": [
                    {
                        "index": chunk.chunk_index,
                        "token_count": chunk.token_count,
                        "text_preview": chunk.text[:100] + "..." if len(chunk.text) > 100 else chunk.text,
                        "metadata": chunk.metadata
                    }
                    for chunk in chunks[:3]  # First 3 chunks
                ]
            }
        else:
            # Basic chunking fallback
            if chunk_method == "paragraph":
                basic_chunks = [p.strip() for p in text.split("\n\n") if p.strip()]
            else:
                basic_chunks = [text]
            
            return {
                "original_text": text,
                "total_chunks": len(basic_chunks),
                "chunk_method": "basic_" + chunk_method,
                "enhanced": False,
                "chunks_preview": [
                    {
                        "index": i,
                        "text_preview": chunk[:100] + "..." if len(chunk) > 100 else chunk
                    }
                    for i, chunk in enumerate(basic_chunks[:3])
                ]
            }
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def cleanup_temp_file(file_path: str):
    """Clean up temporary file"""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.debug(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temp file {file_path}: {e}")
