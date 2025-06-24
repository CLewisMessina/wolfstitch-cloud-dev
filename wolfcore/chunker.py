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
from typing import List, Optional, Dict, Any, Tuple, Callable
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
    
    def chunk_text(self, text: str, tokenizer_func: Optional[Callable[[str], int]] = None) -> List[Chunk]:
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
    
    def _chunk_by_paragraphs(self, text: str, tokenizer_func: Callable[[str], int]) -> List[Chunk]:
        """
        Chunk text by paragraphs, combining until max_tokens reached
        
        This is the most common method for document processing.
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return self._combine_into_chunks(paragraphs, text, tokenizer_func, "\n\n")
    
    def _chunk_by_sentences(self, text: str, tokenizer_func: Callable[[str], int]) -> List[Chunk]:
        """
        Chunk text by sentences, combining until max_tokens reached
        
        Good for fine-grained control and preserving sentence boundaries.
        """
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return self._combine_into_chunks(sentences, text, tokenizer_func, " ")
    
    def _chunk_by_custom_delimiter(self, text: str, tokenizer_func: Callable[[str], int]) -> List[Chunk]:
        """
        Chunk text by custom delimiter
        
        Useful for structured text with specific separators.
        """
        if not self.config.custom_delimiter:
            raise ValueError("Custom delimiter is required for custom chunking method")
        
        parts = [p.strip() for p in text.split(self.config.custom_delimiter) if p.strip()]
        chunks = self._combine_into_chunks(parts, text, tokenizer_func, self.config.custom_delimiter)
        
        # Add separator metadata
        for chunk in chunks:
            chunk.metadata["separator"] = self.config.custom_delimiter
        
        return chunks
    
    def _chunk_token_aware(self, text: str, tokenizer_func: Callable[[str], int]) -> List[Chunk]:
        """
        Token-aware chunking that splits at word boundaries while respecting token limits
        
        This method provides the most precise token control but may break at arbitrary points.
        """
        words = text.split()
        if not words:
            return []
        
        chunks = []
        current_words = []
        current_tokens = 0
        chunk_index = 0
        
        for word in words:
            word_tokens = tokenizer_func(word)
            
            # Check if adding this word would exceed the limit
            if current_tokens + word_tokens > self.config.max_tokens and current_words:
                # Create chunk from current words
                chunk_text = " ".join(current_words)
                chunk = self._create_chunk(
                    chunk_text, current_tokens, chunk_index, text, "token_aware"
                )
                chunks.append(chunk)
                
                # Handle overlap if configured
                if self.config.overlap_tokens > 0:
                    overlap_words = self._get_overlap_words(current_words, tokenizer_func)
                    current_words = overlap_words
                    current_tokens = sum(tokenizer_func(w) for w in overlap_words)
                else:
                    current_words = []
                    current_tokens = 0
                
                chunk_index += 1
            
            current_words.append(word)
            current_tokens += word_tokens
        
        # Create final chunk if there are remaining words
        if current_words:
            chunk_text = " ".join(current_words)
            chunk = self._create_chunk(
                chunk_text, current_tokens, chunk_index, text, "token_aware"
            )
            chunks.append(chunk)
        
        return chunks
    
    def _combine_into_chunks(self, parts: List[str], original_text: str, 
                           tokenizer_func: Callable[[str], int], separator: str) -> List[Chunk]:
        """
        Combine text parts into chunks respecting token limits
        
        Args:
            parts: List of text parts to combine
            original_text: Original text for position calculation
            tokenizer_func: Function to count tokens
            separator: Separator used between parts
            
        Returns:
            List of Chunk objects
        """
        if not parts:
            return []
        
        chunks = []
        current_parts = []
        current_tokens = 0
        chunk_index = 0
        
        for part in parts:
            part_tokens = tokenizer_func(part)
            
            # Check if adding this part would exceed the limit
            if (current_tokens + part_tokens > self.config.max_tokens and 
                current_parts and 
                len(current_parts) > 0):
                
                # Create chunk from current parts
                chunk_text = separator.join(current_parts)
                chunk = self._create_chunk(
                    chunk_text, current_tokens, chunk_index, original_text, self.config.method
                )
                chunks.append(chunk)
                
                # Start new chunk
                current_parts = []
                current_tokens = 0
                chunk_index += 1
            
            current_parts.append(part)
            current_tokens += part_tokens
        
        # Create final chunk if there are remaining parts
        if current_parts:
            chunk_text = separator.join(current_parts)
            chunk = self._create_chunk(
                chunk_text, current_tokens, chunk_index, original_text, self.config.method
            )
            chunks.append(chunk)
        
        return chunks
    
    def _create_chunk(self, text: str, token_count: int, chunk_index: int, 
                     original_text: str, method: str) -> Chunk:
        """
        Create a Chunk object with calculated positions and metadata
        
        Args:
            text: Chunk text content
            token_count: Number of tokens in chunk
            chunk_index: Index of this chunk
            original_text: Original text for position calculation
            method: Chunking method used
            
        Returns:
            Chunk object
        """
        # Calculate positions in original text
        start_pos = original_text.find(text.strip()[:50])  # Use first 50 chars for search
        if start_pos == -1:
            start_pos = 0
        end_pos = start_pos + len(text)
        
        # Create metadata
        metadata = {
            "method": method,
            "max_tokens": self.config.max_tokens,
            "overlap_tokens": self.config.overlap_tokens,
            "character_count": len(text),
            "word_count": len(text.split())
        }
        
        return Chunk(
            text=text,
            token_count=token_count,
            start_position=start_pos,
            end_position=end_pos,
            chunk_index=chunk_index,
            metadata=metadata
        )
    
    def _get_overlap_words(self, words: List[str], tokenizer_func: Callable[[str], int]) -> List[str]:
        """
        Get words for overlap based on overlap_tokens configuration
        
        Args:
            words: List of words from previous chunk
            tokenizer_func: Function to count tokens
            
        Returns:
            List of words for overlap
        """
        if self.config.overlap_tokens <= 0:
            return []
        
        overlap_words = []
        overlap_tokens = 0
        
        # Take words from the end until we reach overlap_tokens
        for word in reversed(words):
            word_tokens = tokenizer_func(word)
            if overlap_tokens + word_tokens <= self.config.overlap_tokens:
                overlap_words.insert(0, word)
                overlap_tokens += word_tokens
            else:
                break
        
        return overlap_words
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Default token estimation function using word count
        
        This provides a reasonable estimate for most use cases.
        For more accurate tokenization, pass a custom tokenizer_func.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        if not text.strip():
            return 0
        
        # Basic word-based estimation (1 word ≈ 1.3 tokens on average)
        words = len(text.split())
        return max(1, int(words * 1.3))


# Utility functions for backward compatibility and simple usage

def split_text(text: str, method: str = "paragraph", delimiter: Optional[str] = None) -> List[str]:
    """
    Simple text splitting function without chunking logic
    
    Args:
        text: Text to split
        method: Split method (paragraph, sentence, custom)
        delimiter: Custom delimiter for custom method
        
    Returns:
        List of text parts
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
                          tokenizer_func: Optional[Callable[[str], int]] = None) -> List[Chunk]:
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
    if config is None:
        config = ChunkingConfig()
    
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
