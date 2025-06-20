"""
Wolfcore - AI Dataset Preparation Library
Enhanced cloud-ready components extracted from Wolfstitch Desktop App

This library provides stateless, cloud-ready components for:
- Multi-format file parsing (PDF, DOCX, TXT, code files)
- Intelligent text preprocessing and cleaning
- Token-aware text chunking with multiple strategies
- Progressive tokenizer loading and management
- Export to multiple training-ready formats

Usage:
    from wolfcore import Wolfstitch
    
    # Simple one-line processing
    result = Wolfstitch().process_file("document.pdf", tokenizer="word-estimate")
    
    # Step-by-step processing  
    from wolfcore.cleaner import clean_text
    from wolfcore.chunker import chunk_text_simple
    
    cleaned = clean_text(raw_text, file_extension='.txt')
    chunks = chunk_text_simple(cleaned, max_tokens=1024)
"""

__version__ = "1.0.0"
__author__ = "Wolfstitch Team"
__email__ = "support@wolfstitch.com"

# Core imports for public API
from .parsers import FileParser, ParsedFile
from .exceptions import WolfcoreError, ProcessingError, ParsingError, UnsupportedFormatError

# Enhanced modules (newly extracted)
try:
    from .cleaner import (
        clean_text, clean_text_async, detect_content_type,
        clean_code_content, clean_document_content, clean_data_content
    )
    CLEANER_AVAILABLE = True
except ImportError:
    CLEANER_AVAILABLE = False

try:
    from .chunker import (
        Chunk, ChunkingConfig, TextChunker,
        split_text, chunk_text_simple, chunk_text_async
    )
    CHUNKER_AVAILABLE = True
except ImportError:
    CHUNKER_AVAILABLE = False

try:
    from .processor import (
        Wolfstitch, ProcessingResult, ProcessingConfig,
        process_file_simple, process_file_simple_async
    )
    PROCESSOR_AVAILABLE = True
except ImportError:
    PROCESSOR_AVAILABLE = False

# Optional imports (premium features - Week 2+)
try:
    from .tokenizer_manager import TokenizerManager
    from .model_database import ModelDatabase
    PREMIUM_FEATURES_AVAILABLE = True
except ImportError:
    PREMIUM_FEATURES_AVAILABLE = False

# Progressive loading support
import threading
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# Global state for progressive loading
_loading_status = {
    'basic_features': True,
    'premium_features': PREMIUM_FEATURES_AVAILABLE,
    'tokenizers_loaded': 2 if not PREMIUM_FEATURES_AVAILABLE else 4,
    'total_tokenizers': 4,
    'loading_progress': 100.0 if PREMIUM_FEATURES_AVAILABLE else 50.0
}


def get_loading_status() -> Dict[str, Any]:
    """
    Get current progressive loading status
    
    Returns:
        Dict with loading status information
    """
    return _loading_status.copy()


def get_supported_tokenizers() -> List[str]:
    """
    Get list of supported tokenizer names
    
    Returns:
        List of tokenizer names
    """
    if PROCESSOR_AVAILABLE:
        try:
            processor = Wolfstitch()
            tokenizers = processor.get_available_tokenizers()
            return [t['name'] for t in tokenizers]
        except Exception:
            pass
    
    # Fallback to basic tokenizers
    return ['word-estimate', 'char-estimate']


def initialize_progressive_loading():
    """
    Initialize progressive loading of premium features
    
    This function starts background loading of premium features
    without blocking the main thread.
    """
    def load_premium_features():
        """Background thread to load premium features"""
        try:
            logger.info("Starting progressive loading of premium features...")
            
            # Simulate loading (replace with actual loading logic in Week 2)
            import time
            time.sleep(2)  # Simulate loading time
            
            # Update status
            global _loading_status
            _loading_status['premium_features'] = True
            _loading_status['tokenizers_loaded'] = 4
            _loading_status['loading_progress'] = 100.0
            
            logger.info("Progressive loading completed successfully")
            
        except Exception as e:
            logger.warning(f"Progressive loading failed: {e}")
    
    # Start background loading if not already available
    if not PREMIUM_FEATURES_AVAILABLE:
        thread = threading.Thread(target=load_premium_features, daemon=True)
        thread.start()


# Convenience functions for common operations
def parse_file(file_path: str):
    """
    Parse a file and return parsed content
    
    Args:
        file_path: Path to file to parse
        
    Returns:
        ParsedFile object with text and metadata
    """
    parser = FileParser()
    return parser.parse(file_path)


def process_file(file_path: str, **kwargs):
    """
    Process a file with default settings
    
    Args:
        file_path: Path to file to process
        **kwargs: Processing options
        
    Returns:
        ProcessingResult with chunks and metadata
    """
    if PROCESSOR_AVAILABLE:
        processor = Wolfstitch()
        return processor.process_file(file_path, **kwargs)
    else:
        raise ImportError("Enhanced processor not available. Please check wolfcore installation.")


# Auto-initialize progressive loading
initialize_progressive_loading()

# Public API exports
__all__ = [
    # Core classes
    'FileParser', 'ParsedFile',
    
    # Enhanced processor (if available)
    'Wolfstitch', 'ProcessingResult', 'ProcessingConfig',
    
    # Cleaner functions (if available)
    'clean_text', 'clean_text_async', 'detect_content_type',
    
    # Chunker classes (if available) 
    'Chunk', 'ChunkingConfig', 'TextChunker',
    'split_text', 'chunk_text_simple', 'chunk_text_async',
    
    # Convenience functions
    'parse_file', 'process_file',
    'get_loading_status', 'get_supported_tokenizers',
    
    # Exceptions
    'WolfcoreError', 'ProcessingError', 'ParsingError', 'UnsupportedFormatError',
    
    # Feature availability flags
    'CLEANER_AVAILABLE', 'CHUNKER_AVAILABLE', 'PROCESSOR_AVAILABLE', 'PREMIUM_FEATURES_AVAILABLE'
]