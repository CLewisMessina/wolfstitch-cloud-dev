"""
Wolfstitch Cloud - Text Chunking Module
Advanced text chunking with multiple strategies for cloud processing

Extracted from desktop app's processing/splitter.py with cloud enhancements:
- Multiple chunking strategies (paragraph, sentence, custom, token-aware)
- Token-based chunking with overlap support
- Async-ready for cloud processing
- Smart boundary detection
- Metadata preservation
"""

import re
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a text chunk with metadata"""
    text: str
    token_count: int
    start_position: int
    end_position: int
    chunk_index: int
    metadata: Dict[str, Any]


@dataclass
class ChunkingConfig:
    """Configuration for text chunking"""
    method: str = "paragraph"  # paragraph, sentence, custom, token_aware
    max_tokens: int = 1024
    overlap_tokens: int = 0
    custom_delimiter: Optional[str] = None
    preserve_boundaries: bool = True
    min_chunk_size: int = 50  # Minimum tokens per chunk


class TextChunker:
    """
    Advanced text chunker with multiple strategies
    
    Supports various chunking methods optimized for different content types
    and use cases in AI dataset preparation.
    """
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        """
        Initialize chunker with configuration
        
        Args:
            config: Chunking configuration, uses defaults if None
        """
        self.config = config or ChunkingConfig()
    
    def chunk_text(self, text: str, tokenizer_func=None) -> List[Chunk]:
        """
        Chunk text using the configured method
        
        Args:
            text: Text to chunk
            tokenizer_func: Function to count tokens (defaults to word count)
            
        Returns:
            List of Chunk objects
        """
        if not text.strip():
            return []
        
        # Default tokenizer function (word-based estimation)
        if tokenizer_func is None:
            tokenizer_func = self._estimate_tokens
        
        logger.debug(f"Chunking text with method={self.config.method}, max_tokens={self.config.max_tokens}")
        
        # Route to appropriate chunking method
        if self.config.method == "paragraph":
            return self._chunk_by_paragraphs(text, tokenizer_func)
        elif self.config.method == "sentence":
            return self._chunk_by_sentences(text, tokenizer_func)
        elif self.config.method == "custom":
            return self._chunk_by_custom_delimiter(text, tokenizer_func)
        elif self.config.method == "token_aware":
            return self._chunk_token_aware(text, tokenizer_func)
        else:
            logger.warning(f"Unknown chunking method: {self.config.method}, falling back to paragraph")
            return self._chunk_by_paragraphs(text, tokenizer_func)
    
    def _chunk_by_paragraphs(self, text: str, tokenizer_func) -> List[Chunk]:
        """
        Chunk text by paragraphs, combining until max_tokens reached
        
        This is the most common method for document processing.
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return self._combine_into_chunks(paragraphs, text, tokenizer_func, "\n\n")
    
    def _chunk_by_sentences(self, text: str, tokenizer_func) -> List[Chunk]:
        """
        Chunk text by sentences, combining until max_tokens reached
        
        Good for fine-grained control and preserving sentence boundaries.
        """
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return self._combine_into_chunks(sentences, text, tokenizer_func, " ")
    
    def _chunk_by_custom_delimiter(self, text: str, tokenizer_func) -> List[Chunk]:
        """
        Chunk text by custom delimiter
        
        Useful for structured text with specific separators.
        """
        if not self.config.custom_delimiter:
            logger.warning("Custom delimiter not specified, falling back to paragraph chunking")
            return self._chunk_by_paragraphs(text, tokenizer_func)
        
        parts = text.split(self.config.custom_delimiter)
        parts = [p.strip() for p in parts if p.strip()]
        return self._combine_into_chunks(parts, text, tokenizer_func, self.config.custom_delimiter)
    
    def _chunk_token_aware(self, text: str, tokenizer_func) -> List[Chunk]:
        """
        Advanced token-aware chunking with sliding window and overlap
        
        This method prioritizes token limits while trying to preserve
        natural boundaries where possible.
        """
        chunks = []
        words = text.split()
        current_chunk_words = []
        current_tokens = 0
        chunk_index = 0
        text_position = 0
        
        for word in words:
            word_tokens = tokenizer_func(word)
            
            # Check if adding this word would exceed max_tokens
            if current_tokens + word_tokens > self.config.max_tokens and current_chunk_words:
                # Create chunk from current words
                chunk_text = " ".join(current_chunk_words)
                chunk_start = text_position - len(chunk_text)
                
                chunk = Chunk(
                    text=chunk_text,
                    token_count=current_tokens,
                    start_position=max(0, chunk_start),
                    end_position=text_position,
                    chunk_index=chunk_index,
                    metadata={
                        "method": "token_aware",
                        "word_count": len(current_chunk_words)
                    }
                )
                chunks.append(chunk)
                
                # Handle overlap if configured
                if self.config.overlap_tokens > 0:
                    overlap_words = self._get_overlap_words(current_chunk_words, tokenizer_func)
                    current_chunk_words = overlap_words
                    current_tokens = sum(tokenizer_func(w) for w in overlap_words)
                else:
                    current_chunk_words = []
                    current_tokens = 0
                
                chunk_index += 1
            
            current_chunk_words.append(word)
            current_tokens += word_tokens
            text_position += len(word) + 1  # +1 for space
        
        # Add final chunk if any words remain
        if current_chunk_words:
            chunk_text = " ".join(current_chunk_words)
            chunk_start = text_position - len(chunk_text)
            
            chunk = Chunk(
                text=chunk_text,
                token_count=current_tokens,
                start_position=max(0, chunk_start),
                end_position=text_position,
                chunk_index=chunk_index,
                metadata={
                    "method": "token_aware",
                    "word_count": len(current_chunk_words)
                }
            )
            chunks.append(chunk)
        
        logger.debug(f"Token-aware chunking created {len(chunks)} chunks")
        return chunks
    
    def _combine_into_chunks(self, parts: List[str], original_text: str, 
                           tokenizer_func, separator: str) -> List[Chunk]:
        """
        Combine text parts into chunks respecting token limits
        
        Args:
            parts: List of text parts to combine
            original_text: Original text for position calculation
            tokenizer_func: Function to count tokens
            separator: Separator used between parts
            
        Returns:
            List of chunks
        """
        chunks = []
        current_parts = []
        current_tokens = 0
        chunk_index = 0
        text_position = 0
        
        for part in parts:
            part_tokens = tokenizer_func(part)
            
            # Check if adding this part would exceed max_tokens
            if current_tokens + part_tokens > self.config.max_tokens and current_parts:
                # Create chunk from current parts
                chunk_text = separator.join(current_parts)
                chunk_start = self._find_text_position(original_text, chunk_text, text_position)
                
                chunk = Chunk(
                    text=chunk_text,
                    token_count=current_tokens,
                    start_position=chunk_start,
                    end_position=chunk_start + len(chunk_text),
                    chunk_index=chunk_index,
                    metadata={
                        "method": self.config.method,
                        "part_count": len(current_parts),
                        "separator": separator
                    }
                )
                chunks.append(chunk)
                
                current_parts = []
                current_tokens = 0
                chunk_index += 1
            
            # Add part to current chunk (even if it exceeds limit by itself)
            current_parts.append(part)
            current_tokens += part_tokens
        
        # Add final chunk if any parts remain
        if current_parts:
            chunk_text = separator.join(current_parts)
            chunk_start = self._find_text_position(original_text, chunk_text, text_position)
            
            chunk = Chunk(
                text=chunk_text,
                token_count=current_tokens,
                start_position=chunk_start,
                end_position=chunk_start + len(chunk_text),
                chunk_index=chunk_index,
                metadata={
                    "method": self.config.method,
                    "part_count": len(current_parts),
                    "separator": separator
                }
            )
            chunks.append(chunk)
        
        logger.debug(f"Combined chunking created {len(chunks)} chunks from {len(parts)} parts")
        return chunks
    
    def _get_overlap_words(self, words: List[str], tokenizer_func) -> List[str]:
        """
        Get overlap words for sliding window chunking
        
        Returns the last N words that fit within the overlap token limit.
        """
        overlap_words = []
        overlap_tokens = 0
        
        # Work backwards from the end of the chunk
        for word in reversed(words):
            word_tokens = tokenizer_func(word)
            if overlap_tokens + word_tokens <= self.config.overlap_tokens:
                overlap_words.insert(0, word)
                overlap_tokens += word_tokens
            else:
                break
        
        return overlap_words
    
    def _find_text_position(self, text: str, chunk_text: str, hint_position: int) -> int:
        """
        Find the position of chunk_text in the original text
        
        Uses hint_position to search efficiently.
        """
        try:
            # Search around the hint position first
            search_start = max(0, hint_position - 100)
            search_end = min(len(text), hint_position + len(chunk_text) + 100)
            search_area = text[search_start:search_end]
            
            position = search_area.find(chunk_text)
            if position != -1:
                return search_start + position
            
            # Fallback to full text search
            position = text.find(chunk_text)
            return max(0, position)
        except Exception:
            # If all else fails, return hint position
            return hint_position
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Simple word-based token estimation
        
        This is a fallback when no tokenizer function is provided.
        Uses a rough 1.3 tokens per word ratio.
        """
        word_count = len(text.split())
        return int(word_count * 1.3)


# Convenience functions for backward compatibility
def split_text(text: str, method: str = "paragraph", delimiter: Optional[str] = None,
               max_tokens: int = 1024) -> List[str]:
    """
    Simple text splitting function for backward compatibility
    
    Args:
        text: Text to split
        method: Splitting method ("paragraph", "sentence", "custom")
        delimiter: Custom delimiter (required if method="custom")
        max_tokens: Maximum tokens per chunk
        
    Returns:
        List of text chunks (strings only, no metadata)
        
    Raises:
        ValueError: If method is invalid or delimiter is missing for custom method
    """
    if method == "paragraph":
        return [p.strip() for p in text.split("\n\n") if p.strip()]
    elif method == "sentence":
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    elif method == "custom":
        if not delimiter:
            raise ValueError("Delimiter is required for custom split method")
        return [s.strip() for s in text.split(delimiter) if s.strip()]
    else:
        raise ValueError(f"Invalid split method: {method}")


def chunk_text_simple(text: str, method: str = "paragraph", max_tokens: int = 1024,
                     delimiter: Optional[str] = None) -> List[Chunk]:
    """
    Simple chunking function with basic configuration
    
    Args:
        text: Text to chunk
        method: Chunking method
        max_tokens: Maximum tokens per chunk
        delimiter: Custom delimiter
        
    Returns:
        List of Chunk objects
    """
    config = ChunkingConfig(
        method=method,
        max_tokens=max_tokens,
        custom_delimiter=delimiter
    )
    chunker = TextChunker(config)
    return chunker.chunk_text(text)


# Async versions for cloud processing
async def chunk_text_async(text: str, config: Optional[ChunkingConfig] = None,
                          tokenizer_func=None) -> List[Chunk]:
    """
    Async wrapper for text chunking to support cloud processing
    
    Args:
        text: Text to chunk
        config: Chunking configuration
        tokenizer_func: Token counting function
        
    Returns:
        List of Chunk objects
    """
    # For now, chunking is CPU-bound and fast enough to run synchronously
    # In future, could use asyncio.to_thread for very large texts
    chunker = TextChunker(config)
    return chunker.chunk_text(text, tokenizer_func)


# Export the main interface
__all__ = [
    'Chunk',
    'ChunkingConfig', 
    'TextChunker',
    'split_text',
    'chunk_text_simple',
    'chunk_text_async'
]