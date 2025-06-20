"""
Wolfstitch Cloud - Enhanced Processing Module
Main orchestrator for file processing pipeline

Enhanced from desktop app's controller.py with cloud optimizations:
- Async-first design for cloud processing
- Integration with cleaner and chunker modules
- Progressive feature loading support
- Comprehensive error handling and logging
- Backward compatibility with desktop API
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field

from .parsers import FileParser, ParsedFile
from .cleaner import clean_text_async, detect_content_type
from .chunker import TextChunker, ChunkingConfig, Chunk
from .exceptions import ProcessingError, ParsingError, CleaningError, ChunkingError

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Complete result of file processing"""
    chunks: List[Chunk]
    total_chunks: int
    total_tokens: int
    total_characters: int
    processing_time: float
    file_info: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingConfig:
    """Configuration for file processing"""
    # Cleaning options
    remove_headers: bool = True
    normalize_whitespace: bool = True
    strip_bullets: bool = True
    
    # Chunking options
    chunk_method: str = "paragraph"  # paragraph, sentence, custom, token_aware
    max_tokens: int = 1024
    overlap_tokens: int = 0
    custom_delimiter: Optional[str] = None
    
    # Tokenizer options
    tokenizer: str = "word-estimate"
    
    # Processing options
    preserve_structure: bool = True
    include_metadata: bool = True


class Wolfstitch:
    """
    Enhanced Wolfstitch processor for cloud processing
    
    This is the main orchestrator that coordinates file parsing, text cleaning,
    and chunking. It provides both sync and async interfaces for flexibility.
    """
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        """
        Initialize Wolfstitch processor
        
        Args:
            config: Processing configuration, uses defaults if None
        """
        self.config = config or ProcessingConfig()
        self.file_parser = FileParser()
        self._tokenizer_func: Optional[Callable] = None
        self._progressive_features_loaded = False
        
        logger.debug(f"Wolfstitch processor initialized with config: {self.config}")
    
    def process_file(self, file_path: Union[str, Path], 
                    tokenizer: Optional[str] = None,
                    max_tokens: Optional[int] = None,
                    **kwargs) -> ProcessingResult:
        """
        Process a file synchronously (backward compatibility)
        
        Args:
            file_path: Path to file to process
            tokenizer: Tokenizer to use (overrides config)
            max_tokens: Max tokens per chunk (overrides config)
            **kwargs: Additional processing options
            
        Returns:
            ProcessingResult with chunks and metadata
        """
        return asyncio.run(self.process_file_async(file_path, tokenizer, max_tokens, **kwargs))
    
    async def process_file_async(self, file_path: Union[str, Path],
                               tokenizer: Optional[str] = None,
                               max_tokens: Optional[int] = None,
                               **kwargs) -> ProcessingResult:
        """
        Process a file asynchronously
        
        This is the main processing pipeline:
        1. Parse file to extract text
        2. Clean text based on content type
        3. Chunk text according to configuration
        4. Calculate statistics and metadata
        
        Args:
            file_path: Path to file to process
            tokenizer: Tokenizer to use (overrides config)
            max_tokens: Max tokens per chunk (overrides config)
            **kwargs: Additional processing options (override config)
            
        Returns:
            ProcessingResult with chunks and metadata
        """
        start_time = time.time()
        file_path = Path(file_path)
        
        try:
            logger.info(f"Starting async processing of {file_path}")
            
            # Update config with any overrides
            processing_config = self._merge_config_overrides(tokenizer, max_tokens, **kwargs)
            
            # Step 1: Parse file
            parsed_file = await self._parse_file_async(file_path)
            
            # Step 2: Clean text
            cleaned_text = await self._clean_text_async(parsed_file, processing_config)
            
            # Step 3: Chunk text
            chunks = await self._chunk_text_async(cleaned_text, parsed_file, processing_config)
            
            # Step 4: Calculate statistics
            result = self._build_processing_result(
                chunks, parsed_file, time.time() - start_time, processing_config
            )
            
            logger.info(f"Processing complete: {result.total_chunks} chunks, "
                       f"{result.total_tokens} tokens, {result.processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Processing failed for {file_path}: {e}")
            raise ProcessingError(f"Failed to process {file_path}: {str(e)}") from e
    
    async def _parse_file_async(self, file_path: Path) -> ParsedFile:
        """Parse file to extract text and metadata"""
        try:
            # Run parsing in thread pool for true async
            parsed_file = await asyncio.to_thread(self.file_parser.parse, str(file_path))
            logger.debug(f"Parsed {file_path}: {len(parsed_file.text)} characters")
            return parsed_file
        except Exception as e:
            raise ParsingError(f"Failed to parse {file_path}: {str(e)}") from e
    
    async def _clean_text_async(self, parsed_file: ParsedFile, 
                              config: ProcessingConfig) -> str:
        """Clean text based on content type and configuration"""
        try:
            # Determine content type from file extension
            content_type = detect_content_type(parsed_file.format)
            
            cleaned_text = await clean_text_async(
                parsed_file.text,
                file_extension=parsed_file.format,
                content_type=content_type,
                remove_headers=config.remove_headers,
                normalize_whitespace=config.normalize_whitespace,
                strip_bullets=config.strip_bullets
            )
            
            logger.debug(f"Cleaned text: {len(parsed_file.text)} -> {len(cleaned_text)} characters")
            return cleaned_text
            
        except Exception as e:
            raise CleaningError(f"Failed to clean text: {str(e)}") from e
    
    async def _chunk_text_async(self, text: str, parsed_file: ParsedFile,
                              config: ProcessingConfig) -> List[Chunk]:
        """Chunk text according to configuration"""
        try:
            # Create chunking configuration
            chunk_config = ChunkingConfig(
                method=config.chunk_method,
                max_tokens=config.max_tokens,
                overlap_tokens=config.overlap_tokens,
                custom_delimiter=config.custom_delimiter
            )
            
            # Get tokenizer function
            tokenizer_func = self._get_tokenizer_function(config.tokenizer)
            
            # Create chunker and process
            chunker = TextChunker(chunk_config)
            chunks = await asyncio.to_thread(chunker.chunk_text, text, tokenizer_func)
            
            logger.debug(f"Chunked text into {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            raise ChunkingError(f"Failed to chunk text: {str(e)}") from e
    
    def _merge_config_overrides(self, tokenizer: Optional[str] = None,
                              max_tokens: Optional[int] = None,
                              **kwargs) -> ProcessingConfig:
        """Merge configuration overrides with default config"""
        # Create a copy of the current config
        config_dict = {
            'remove_headers': kwargs.get('remove_headers', self.config.remove_headers),
            'normalize_whitespace': kwargs.get('normalize_whitespace', self.config.normalize_whitespace),
            'strip_bullets': kwargs.get('strip_bullets', self.config.strip_bullets),
            'chunk_method': kwargs.get('chunk_method', self.config.chunk_method),
            'max_tokens': max_tokens or kwargs.get('max_tokens', self.config.max_tokens),
            'overlap_tokens': kwargs.get('overlap_tokens', self.config.overlap_tokens),
            'custom_delimiter': kwargs.get('custom_delimiter', self.config.custom_delimiter),
            'tokenizer': tokenizer or kwargs.get('tokenizer', self.config.tokenizer),
            'preserve_structure': kwargs.get('preserve_structure', self.config.preserve_structure),
            'include_metadata': kwargs.get('include_metadata', self.config.include_metadata)
        }
        
        return ProcessingConfig(**config_dict)
    
    def _get_tokenizer_function(self, tokenizer_name: str) -> Callable[[str], int]:
        """Get tokenizer function by name"""
        # For Week 1, use simple word-based estimation
        # In Week 2, this will integrate with the tokenizer manager
        if tokenizer_name == "word-estimate":
            return self._estimate_tokens_word_based
        elif tokenizer_name == "char-estimate":
            return self._estimate_tokens_char_based
        else:
            logger.warning(f"Unknown tokenizer {tokenizer_name}, using word-estimate")
            return self._estimate_tokens_word_based
    
    def _estimate_tokens_word_based(self, text: str) -> int:
        """Estimate tokens using word count (1.3x multiplier)"""
        word_count = len(text.split())
        return int(word_count * 1.3)
    
    def _estimate_tokens_char_based(self, text: str) -> int:
        """Estimate tokens using character count (4 chars per token)"""
        return len(text) // 4
    
    def _build_processing_result(self, chunks: List[Chunk], parsed_file: ParsedFile,
                               processing_time: float, config: ProcessingConfig) -> ProcessingResult:
        """Build final processing result with statistics"""
        total_tokens = sum(chunk.token_count for chunk in chunks)
        total_characters = sum(len(chunk.text) for chunk in chunks)
        
        file_info = {
            'filename': parsed_file.filename,
            'format': parsed_file.format,
            'size_bytes': parsed_file.size_bytes,
            'encoding': parsed_file.encoding,
            'original_length': len(parsed_file.text)
        }
        
        metadata = {
            'processing_config': {
                'tokenizer': config.tokenizer,
                'chunk_method': config.chunk_method,
                'max_tokens': config.max_tokens,
                'overlap_tokens': config.overlap_tokens
            },
            'statistics': {
                'avg_tokens_per_chunk': total_tokens / len(chunks) if chunks else 0,
                'avg_chars_per_chunk': total_characters / len(chunks) if chunks else 0,
                'compression_ratio': total_characters / len(parsed_file.text) if parsed_file.text else 0
            }
        }
        
        return ProcessingResult(
            chunks=chunks,
            total_chunks=len(chunks),
            total_tokens=total_tokens,
            total_characters=total_characters,
            processing_time=processing_time,
            file_info=file_info,
            metadata=metadata
        )
    
    # Progressive feature methods for cloud compatibility
    def get_available_tokenizers(self) -> List[Dict[str, Any]]:
        """Get list of available tokenizers"""
        # Week 1 basic tokenizers
        tokenizers = [
            {
                'name': 'word-estimate',
                'display_name': 'Word Estimate',
                'description': 'Fast word-based token estimation',
                'loading_status': 'loaded',
                'tier': 'free'
            },
            {
                'name': 'char-estimate', 
                'display_name': 'Character Estimate',
                'description': 'Character-based token estimation',
                'loading_status': 'loaded',
                'tier': 'free'
            }
        ]
        
        # Week 2+: Add premium tokenizers
        if self._progressive_features_loaded:
            tokenizers.extend([
                {
                    'name': 'gpt-2',
                    'display_name': 'GPT-2',
                    'description': 'OpenAI GPT-2 tokenizer',
                    'loading_status': 'loaded',
                    'tier': 'premium'
                },
                {
                    'name': 'gpt-4',
                    'display_name': 'GPT-4',
                    'description': 'OpenAI GPT-4 tokenizer',
                    'loading_status': 'loaded', 
                    'tier': 'premium'
                }
            ])
        
        return tokenizers
    
    def get_loading_status(self) -> Dict[str, Any]:
        """Get progressive loading status"""
        return {
            'basic_features': True,
            'premium_features': self._progressive_features_loaded,
            'tokenizers_loaded': 2 + (2 if self._progressive_features_loaded else 0),
            'total_tokenizers': 4,
            'loading_progress': 100.0 if self._progressive_features_loaded else 50.0
        }


# Convenience functions for backward compatibility and simple usage
def process_file_simple(file_path: Union[str, Path], 
                       tokenizer: str = "word-estimate",
                       max_tokens: int = 1024) -> ProcessingResult:
    """
    Simple file processing function
    
    Args:
        file_path: Path to file
        tokenizer: Tokenizer name
        max_tokens: Maximum tokens per chunk
        
    Returns:
        ProcessingResult
    """
    processor = Wolfstitch()
    return processor.process_file(file_path, tokenizer, max_tokens)


async def process_file_simple_async(file_path: Union[str, Path],
                                  tokenizer: str = "word-estimate", 
                                  max_tokens: int = 1024) -> ProcessingResult:
    """
    Simple async file processing function
    
    Args:
        file_path: Path to file
        tokenizer: Tokenizer name  
        max_tokens: Maximum tokens per chunk
        
    Returns:
        ProcessingResult
    """
    processor = Wolfstitch()
    return await processor.process_file_async(file_path, tokenizer, max_tokens)


# Global functions for compatibility with existing code
def get_supported_tokenizers() -> List[str]:
    """Get list of supported tokenizer names"""
    processor = Wolfstitch()
    tokenizers = processor.get_available_tokenizers()
    return [t['name'] for t in tokenizers]


def get_loading_status() -> Dict[str, Any]:
    """Get current loading status"""
    processor = Wolfstitch()
    return processor.get_loading_status()


# Export the main interface
__all__ = [
    'Wolfstitch',
    'ProcessingResult',
    'ProcessingConfig',
    'process_file_simple',
    'process_file_simple_async',
    'get_supported_tokenizers',
    'get_loading_status'
]