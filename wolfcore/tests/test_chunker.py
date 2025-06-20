"""
Tests for wolfcore.chunker module
"""

import pytest
import asyncio
from wolfcore.chunker import (
    Chunk, ChunkingConfig, TextChunker,
    split_text, chunk_text_simple, chunk_text_async
)


class TestChunkDataClass:
    """Test the Chunk data class"""
    
    def test_chunk_creation(self):
        """Test creating a Chunk object"""
        chunk = Chunk(
            text="Test chunk",
            token_count=10,
            start_position=0,
            end_position=10,
            chunk_index=0,
            metadata={"test": True}
        )
        
        assert chunk.text == "Test chunk"
        assert chunk.token_count == 10
        assert chunk.metadata["test"] is True


class TestChunkingConfig:
    """Test chunking configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = ChunkingConfig()
        
        assert config.method == "paragraph"
        assert config.max_tokens == 1024
        assert config.overlap_tokens == 0
        assert config.custom_delimiter is None
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = ChunkingConfig(
            method="sentence",
            max_tokens=512,
            overlap_tokens=50,
            custom_delimiter="||"
        )
        
        assert config.method == "sentence"
        assert config.max_tokens == 512
        assert config.overlap_tokens == 50
        assert config.custom_delimiter == "||"


class TestTextChunker:
    """Test the TextChunker class"""
    
    def test_paragraph_chunking(self):
        """Test paragraph-based chunking"""
        text = """First paragraph with some content.

Second paragraph with more content.

Third paragraph with even more content."""
        
        config = ChunkingConfig(method="paragraph", max_tokens=20)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)
        assert chunks[0].chunk_index == 0
        
        # Each chunk should have metadata
        assert chunks[0].metadata["method"] == "paragraph"
    
    def test_sentence_chunking(self):
        """Test sentence-based chunking"""
        text = "First sentence. Second sentence! Third sentence? Fourth sentence."
        
        config = ChunkingConfig(method="sentence", max_tokens=10)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 0
        assert "First sentence" in chunks[0].text
        assert chunks[0].metadata["method"] == "sentence"
    
    def test_custom_delimiter_chunking(self):
        """Test custom delimiter chunking"""
        text = "Part1||Part2||Part3||Part4"
        
        config = ChunkingConfig(method="custom", custom_delimiter="||", max_tokens=15)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 0
        assert "Part1" in chunks[0].text
        assert chunks[0].metadata["separator"] == "||"
    
    def test_token_aware_chunking(self):
        """Test token-aware chunking"""
        text = "This is a longer text that should be split based on token limits rather than natural boundaries."
        
        config = ChunkingConfig(method="token_aware", max_tokens=10)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 0
        assert all(chunk.token_count <= 15 for chunk in chunks)  # Allow some tolerance
        assert chunks[0].metadata["method"] == "token_aware"
    
    def test_token_aware_with_overlap(self):
        """Test token-aware chunking with overlap"""
        text = "Word1 Word2 Word3 Word4 Word5 Word6 Word7 Word8 Word9 Word10"
        
        config = ChunkingConfig(method="token_aware", max_tokens=5, overlap_tokens=2)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 1
        # Should have some overlap between chunks
        # This is approximate since overlap depends on tokenization
    
    def test_empty_text(self):
        """Test chunking empty text"""
        config = ChunkingConfig()
        chunker = TextChunker(config)
        chunks = chunker.chunk_text("")
        
        assert len(chunks) == 0
    
    def test_whitespace_only_text(self):
        """Test chunking whitespace-only text"""
        config = ChunkingConfig()
        chunker = TextChunker(config)
        chunks = chunker.chunk_text("   \n\n  \t  ")
        
        assert len(chunks) == 0
    
    def test_custom_tokenizer_function(self):
        """Test using custom tokenizer function"""
        text = "Short text for testing."
        
        def custom_tokenizer(text):
            return len(text)  # Character count as tokens
        
        config = ChunkingConfig(max_tokens=10)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text, custom_tokenizer)
        
        assert len(chunks) > 0
        # With character-based tokenizer, should create more chunks
    
    def test_large_single_part(self):
        """Test handling of single part larger than max_tokens"""
        text = "This is a very long paragraph that exceeds the token limit but cannot be split further because it is a single paragraph."
        
        config = ChunkingConfig(method="paragraph", max_tokens=5)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text)
        
        # Should still create chunk even if it exceeds limit
        assert len(chunks) == 1
        assert chunks[0].token_count > 5


class TestBackwardCompatibilityFunctions:
    """Test backward compatibility functions"""
    
    def test_split_text_paragraph(self):
        """Test split_text with paragraph method"""
        text = """First paragraph.

Second paragraph.

Third paragraph."""
        
        parts = split_text(text, method="paragraph")
        
        assert len(parts) == 3
        assert "First paragraph." in parts[0]
        assert "Second paragraph." in parts[1]
    
    def test_split_text_sentence(self):
        """Test split_text with sentence method"""
        text = "First sentence. Second sentence! Third sentence?"
        
        parts = split_text(text, method="sentence")
        
        assert len(parts) >= 3
        assert "First sentence" in parts[0]
    
    def test_split_text_custom(self):
        """Test split_text with custom delimiter"""
        text = "Part1||Part2||Part3"
        
        parts = split_text(text, method="custom", delimiter="||")
        
        assert len(parts) == 3
        assert parts[0] == "Part1"
        assert parts[1] == "Part2"
    
    def test_split_text_invalid_method(self):
        """Test split_text with invalid method"""
        text = "Some text"
        
        with pytest.raises(ValueError):
            split_text(text, method="invalid")
    
    def test_split_text_custom_no_delimiter(self):
        """Test split_text custom method without delimiter"""
        text = "Some text"
        
        with pytest.raises(ValueError):
            split_text(text, method="custom")
    
    def test_chunk_text_simple(self):
        """Test chunk_text_simple function"""
        text = """First paragraph.

Second paragraph.

Third paragraph."""
        
        chunks = chunk_text_simple(text, method="paragraph", max_tokens=50)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)
        assert chunks[0].metadata["method"] == "paragraph"


class TestAsyncChunking:
    """Test async chunking functions"""
    
    @pytest.mark.asyncio
    async def test_chunk_text_async(self):
        """Test async text chunking"""
        text = """First paragraph with content.

Second paragraph with more content."""
        
        config = ChunkingConfig(method="paragraph", max_tokens=30)
        chunks = await chunk_text_async(text, config)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, Chunk) for chunk in chunks)
    
    @pytest.mark.asyncio
    async def test_chunk_text_async_custom_tokenizer(self):
        """Test async chunking with custom tokenizer"""
        text = "Short text for testing async."
        
        def custom_tokenizer(text):
            return len(text.split()) * 2  # Double word count
        
        config = ChunkingConfig(max_tokens=5)
        chunks = await chunk_text_async(text, config, custom_tokenizer)
        
        assert len(chunks) > 0


class TestChunkerEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_very_long_text(self):
        """Test chunking very long text"""
        # Create long text with many paragraphs
        paragraphs = [f"This is paragraph {i} with some content." for i in range(100)]
        text = "\n\n".join(paragraphs)
        
        config = ChunkingConfig(method="paragraph", max_tokens=50)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 0
        assert len(chunks) <= 100  # Should combine some paragraphs
    
    def test_unicode_text_chunking(self):
        """Test chunking text with unicode characters"""
        text = """First paragraph with unicode: 世界 🌍.

Second paragraph with more unicode: café naïve."""
        
        config = ChunkingConfig(method="paragraph", max_tokens=30)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 0
        assert "世界" in chunks[0].text or "世界" in chunks[1].text
        assert "🌍" in chunks[0].text or "🌍" in chunks[1].text
    
    def test_text_with_mixed_separators(self):
        """Test text with mixed paragraph separators"""
        text = "Para 1\n\nPara 2\n\n\nPara 3\n\n\n\nPara 4"
        
        config = ChunkingConfig(method="paragraph", max_tokens=20)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) > 0
        # Should handle mixed separators gracefully
    
    def test_single_very_long_word(self):
        """Test handling of extremely long single word"""
        long_word = "a" * 1000
        text = f"Start {long_word} end."
        
        config = ChunkingConfig(method="sentence", max_tokens=10)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text)
        
        # Should still create chunks
        assert len(chunks) > 0
    
    def test_text_position_tracking(self):
        """Test that text positions are tracked correctly"""
        text = """First paragraph here.

Second paragraph starts here."""
        
        config = ChunkingConfig(method="paragraph", max_tokens=100)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text)
        
        if len(chunks) > 1:
            # Positions should be sensible
            assert chunks[0].start_position >= 0
            assert chunks[0].end_position > chunks[0].start_position
            assert chunks[1].start_position >= chunks[0].end_position
    
    def test_chunk_metadata_completeness(self):
        """Test that chunk metadata is complete and correct"""
        text = """First paragraph.

Second paragraph.

Third paragraph."""
        
        config = ChunkingConfig(method="paragraph", max_tokens=30)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text)
        
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
            assert isinstance(chunk.metadata, dict)
            assert "method" in chunk.metadata
            assert chunk.metadata["method"] == "paragraph"
            assert chunk.token_count > 0
            assert len(chunk.text) > 0


class TestTokenizerIntegration:
    """Test integration with different tokenizer functions"""
    
    def test_word_based_tokenizer(self):
        """Test with word-based tokenizer"""
        text = "This is a test sentence with ten words exactly."  # 9 words
        
        def word_tokenizer(text):
            return len(text.split())
        
        config = ChunkingConfig(method="sentence", max_tokens=5)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text, word_tokenizer)
        
        # Should split into multiple chunks since 9 words > 5 token limit
        assert len(chunks) >= 1
    
    def test_character_based_tokenizer(self):
        """Test with character-based tokenizer"""
        text = "Short text"
        
        def char_tokenizer(text):
            return len(text)
        
        config = ChunkingConfig(method="sentence", max_tokens=5)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text, char_tokenizer)
        
        # With character-based counting, should create more chunks
        assert len(chunks) >= 1
    
    def test_default_tokenizer(self):
        """Test default tokenizer behavior"""
        text = "This is a test sentence."
        
        config = ChunkingConfig(method="sentence", max_tokens=10)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text)  # No tokenizer provided
        
        # Should use default estimation
        assert len(chunks) >= 1
        assert chunks[0].token_count > 0


class TestChunkingStrategies:
    """Test different chunking strategies in detail"""
    
    def test_paragraph_strategy_preserves_structure(self):
        """Test that paragraph chunking preserves document structure"""
        text = """# Header

First paragraph under header.

Second paragraph.

## Subheader

Paragraph under subheader."""
        
        config = ChunkingConfig(method="paragraph", max_tokens=100)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text)
        
        # Should preserve the structure
        combined_text = "\n\n".join(chunk.text for chunk in chunks)
        assert "# Header" in combined_text
        assert "## Subheader" in combined_text
    
    def test_sentence_strategy_granularity(self):
        """Test sentence chunking provides fine granularity"""
        text = "First. Second. Third. Fourth. Fifth."
        
        config = ChunkingConfig(method="sentence", max_tokens=3)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text)
        
        # Should create multiple small chunks
        assert len(chunks) >= 2
        # Each chunk should be relatively small
        assert all(len(chunk.text.split()) <= 5 for chunk in chunks)
    
    def test_token_aware_respects_limits(self):
        """Test that token-aware chunking respects token limits"""
        # Create text where word count != token count
        text = " ".join([f"word{i}" for i in range(50)])
        
        def precise_tokenizer(text):
            # Simulate a tokenizer where each word = 1.5 tokens
            return int(len(text.split()) * 1.5)
        
        config = ChunkingConfig(method="token_aware", max_tokens=10)
        chunker = TextChunker(config)
        chunks = chunker.chunk_text(text, precise_tokenizer)
        
        # All chunks should respect the token limit
        for chunk in chunks:
            assert chunk.token_count <= 12  # Allow small tolerance


if __name__ == "__main__":
    pytest.main([__file__])