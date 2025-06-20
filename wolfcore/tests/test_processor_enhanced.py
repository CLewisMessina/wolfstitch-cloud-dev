"""
Tests for wolfcore.processor module (enhanced version)
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from wolfcore.processor import (
    Wolfstitch, ProcessingResult, ProcessingConfig,
    process_file_simple, process_file_simple_async,
    get_supported_tokenizers, get_loading_status
)
from wolfcore.exceptions import ProcessingError, ParsingError


class TestProcessingConfig:
    """Test processing configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = ProcessingConfig()
        
        assert config.remove_headers is True
        assert config.normalize_whitespace is True
        assert config.strip_bullets is True
        assert config.chunk_method == "paragraph"
        assert config.max_tokens == 1024
        assert config.overlap_tokens == 0
        assert config.tokenizer == "word-estimate"
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = ProcessingConfig(
            remove_headers=False,
            chunk_method="sentence",
            max_tokens=512,
            tokenizer="char-estimate"
        )
        
        assert config.remove_headers is False
        assert config.chunk_method == "sentence"
        assert config.max_tokens == 512
        assert config.tokenizer == "char-estimate"


class TestProcessingResult:
    """Test processing result data structure"""
    
    def test_processing_result_creation(self):
        """Test creating a ProcessingResult"""
        from wolfcore.chunker import Chunk
        
        chunks = [
            Chunk("Test chunk 1", 10, 0, 10, 0, {}),
            Chunk("Test chunk 2", 15, 11, 25, 1, {})
        ]
        
        result = ProcessingResult(
            chunks=chunks,
            total_chunks=2,
            total_tokens=25,
            total_characters=24,
            processing_time=1.5,
            file_info={"filename": "test.txt"},
            metadata={"test": True}
        )
        
        assert len(result.chunks) == 2
        assert result.total_chunks == 2
        assert result.total_tokens == 25
        assert result.processing_time == 1.5
        assert result.metadata["test"] is True


class TestWolfstitchProcessor:
    """Test the main Wolfstitch processor class"""
    
    def test_processor_initialization(self):
        """Test processor initialization"""
        processor = Wolfstitch()
        
        assert processor.config is not None
        assert processor.file_parser is not None
        assert isinstance(processor.config, ProcessingConfig)
    
    def test_processor_with_custom_config(self):
        """Test processor with custom configuration"""
        config = ProcessingConfig(max_tokens=512, tokenizer="char-estimate")
        processor = Wolfstitch(config)
        
        assert processor.config.max_tokens == 512
        assert processor.config.tokenizer == "char-estimate"
    
    def test_get_available_tokenizers(self):
        """Test getting available tokenizers"""
        processor = Wolfstitch()
        tokenizers = processor.get_available_tokenizers()
        
        assert len(tokenizers) >= 2
        assert any(t['name'] == 'word-estimate' for t in tokenizers)
        assert any(t['name'] == 'char-estimate' for t in tokenizers)
        
        # Check structure
        for tokenizer in tokenizers:
            assert 'name' in tokenizer
            assert 'display_name' in tokenizer
            assert 'description' in tokenizer
            assert 'loading_status' in tokenizer
            assert 'tier' in tokenizer
    
    def test_get_loading_status(self):
        """Test getting loading status"""
        processor = Wolfstitch()
        status = processor.get_loading_status()
        
        assert 'basic_features' in status
        assert 'premium_features' in status
        assert 'tokenizers_loaded' in status
        assert 'loading_progress' in status
        
        assert status['basic_features'] is True
        assert isinstance(status['loading_progress'], float)


class TestFileProcessing:
    """Test file processing functionality"""
    
    def create_temp_file(self, content: str, suffix: str = ".txt") -> Path:
        """Helper to create temporary file"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False)
        temp_file.write(content)
        temp_file.close()
        return Path(temp_file.name)
    
    def test_process_simple_text_file(self):
        """Test processing a simple text file"""
        content = """First paragraph with some content.

Second paragraph with more content.

Third paragraph here."""
        
        temp_file = self.create_temp_file(content)
        
        try:
            processor = Wolfstitch()
            result = processor.process_file(temp_file)
            
            assert isinstance(result, ProcessingResult)
            assert result.total_chunks > 0
            assert result.total_tokens > 0
            assert result.processing_time > 0
            assert result.file_info['filename'] == temp_file.name
            
            # Check chunks
            assert len(result.chunks) == result.total_chunks
            assert all(chunk.text.strip() for chunk in result.chunks)
            
        finally:
            temp_file.unlink()
    
    @pytest.mark.asyncio
    async def test_process_file_async(self):
        """Test async file processing"""
        content = "Test content for async processing."
        temp_file = self.create_temp_file(content)
        
        try:
            processor = Wolfstitch()
            result = await processor.process_file_async(temp_file)
            
            assert isinstance(result, ProcessingResult)
            assert result.total_chunks > 0
            assert "Test content" in result.chunks[0].text
            
        finally:
            temp_file.unlink()
    
    def test_process_with_custom_tokenizer(self):
        """Test processing with custom tokenizer"""
        content = "Short test content."
        temp_file = self.create_temp_file(content)
        
        try:
            processor = Wolfstitch()
            result = processor.process_file(temp_file, tokenizer="char-estimate")
            
            assert isinstance(result, ProcessingResult)
            assert result.metadata['processing_config']['tokenizer'] == "char-estimate"
            
        finally:
            temp_file.unlink()
    
    def test_process_with_custom_max_tokens(self):
        """Test processing with custom max tokens"""
        content = """Very long paragraph with lots of content that should be split into multiple chunks when using a small max_tokens value for testing purposes."""
        
        temp_file = self.create_temp_file(content)
        
        try:
            processor = Wolfstitch()
            result = processor.process_file(temp_file, max_tokens=20)
            
            assert isinstance(result, ProcessingResult)
            assert result.metadata['processing_config']['max_tokens'] == 20
            # Should create multiple chunks due to low token limit
            assert result.total_chunks > 1
            
        finally:
            temp_file.unlink()
    
    def test_process_code_file(self):
        """Test processing a code file"""
        code_content = '''def hello_world():
    """A simple function."""
    print("Hello, World!")
    
    if True:
        print("This is Python code")

def another_function():
    pass'''
        
        temp_file = self.create_temp_file(code_content, ".py")
        
        try:
            processor = Wolfstitch()
            result = processor.process_file(temp_file)
            
            assert isinstance(result, ProcessingResult)
            assert result.total_chunks > 0
            
            # Code structure should be preserved
            combined_text = "\n".join(chunk.text for chunk in result.chunks)
            assert "def hello_world():" in combined_text
            assert "    print(" in combined_text  # Indentation preserved
            
        finally:
            temp_file.unlink()
    
    def test_process_with_kwargs_override(self):
        """Test processing with kwargs overriding config"""
        content = "Test content for override testing."
        temp_file = self.create_temp_file(content)
        
        try:
            config = ProcessingConfig(chunk_method="paragraph")
            processor = Wolfstitch(config)
            
            result = processor.process_file(
                temp_file, 
                chunk_method="sentence",
                remove_headers=False
            )
            
            assert isinstance(result, ProcessingResult)
            # Should use overridden values
            assert result.metadata['processing_config']['chunk_method'] == "sentence"
            
        finally:
            temp_file.unlink()


class TestErrorHandling:
    """Test error handling in processing"""
    
    def test_nonexistent_file(self):
        """Test processing nonexistent file"""
        processor = Wolfstitch()
        
        with pytest.raises(ProcessingError):
            processor.process_file("nonexistent_file.txt")
    
    @pytest.mark.asyncio
    async def test_nonexistent_file_async(self):
        """Test async processing of nonexistent file"""
        processor = Wolfstitch()
        
        with pytest.raises(ProcessingError):
            await processor.process_file_async("nonexistent_file.txt")
    
    def test_empty_file(self):
        """Test processing empty file"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=".txt", delete=False)
        temp_file.write("")
        temp_file.close()
        
        try:
            processor = Wolfstitch()
            result = processor.process_file(temp_file.name)
            
            # Should handle empty file gracefully
            assert isinstance(result, ProcessingResult)
            assert result.total_chunks == 0
            
        finally:
            Path(temp_file.name).unlink()
    
    @patch('wolfcore.processor.FileParser')
    def test_parsing_error_handling(self, mock_parser_class):
        """Test handling of parsing errors"""
        # Mock parser to raise an exception
        mock_parser = Mock()
        mock_parser.parse.side_effect = Exception("Parsing failed")
        mock_parser_class.return_value = mock_parser
        
        processor = Wolfstitch()
        
        with pytest.raises(ProcessingError):
            processor.process_file("test.txt")


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def create_temp_file(self, content: str, suffix: str = ".txt") -> Path:
        """Helper to create temporary file"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False)
        temp_file.write(content)
        temp_file.close()
        return Path(temp_file.name)
    
    def test_process_file_simple(self):
        """Test simple processing function"""
        content = "Simple test content."
        temp_file = self.create_temp_file(content)
        
        try:
            result = process_file_simple(temp_file)
            
            assert isinstance(result, ProcessingResult)
            assert result.total_chunks > 0
            
        finally:
            temp_file.unlink()
    
    @pytest.mark.asyncio
    async def test_process_file_simple_async(self):
        """Test simple async processing function"""
        content = "Simple async test content."
        temp_file = self.create_temp_file(content)
        
        try:
            result = await process_file_simple_async(temp_file)
            
            assert isinstance(result, ProcessingResult)
            assert result.total_chunks > 0
            
        finally:
            temp_file.unlink()
    
    def test_get_supported_tokenizers_global(self):
        """Test global get_supported_tokenizers function"""
        tokenizers = get_supported_tokenizers()
        
        assert isinstance(tokenizers, list)
        assert len(tokenizers) >= 2
        assert 'word-estimate' in tokenizers
        assert 'char-estimate' in tokenizers
    
    def test_get_loading_status_global(self):
        """Test global get_loading_status function"""
        status = get_loading_status()
        
        assert isinstance(status, dict)
        assert 'basic_features' in status
        assert 'premium_features' in status


class TestConfigMerging:
    """Test configuration merging logic"""
    
    def test_merge_config_overrides(self):
        """Test merging configuration overrides"""
        config = ProcessingConfig(
            max_tokens=1024,
            tokenizer="word-estimate",
            chunk_method="paragraph"
        )
        
        processor = Wolfstitch(config)
        
        merged = processor._merge_config_overrides(
            tokenizer="char-estimate",
            max_tokens=512,
            chunk_method="sentence"
        )
        
        assert merged.tokenizer == "char-estimate"
        assert merged.max_tokens == 512
        assert merged.chunk_method == "sentence"
        # Unchanged values should remain
        assert merged.remove_headers == config.remove_headers
    
    def test_partial_config_override(self):
        """Test partial configuration override"""
        config = ProcessingConfig(max_tokens=1024, tokenizer="word-estimate")
        processor = Wolfstitch(config)
        
        merged = processor._merge_config_overrides(max_tokens=512)
        
        assert merged.max_tokens == 512
        assert merged.tokenizer == "word-estimate"  # Unchanged


class TestTokenizerFunctions:
    """Test tokenizer functions"""
    
    def test_word_based_tokenizer(self):
        """Test word-based token estimation"""
        processor = Wolfstitch()
        
        # Test with known text
        text = "This is a test sentence"  # 5 words
        tokens = processor._estimate_tokens_word_based(text)
        
        # Should be approximately 5 * 1.3 = 6.5, rounded to 6
        assert tokens == 6
    
    def test_char_based_tokenizer(self):
        """Test character-based token estimation"""
        processor = Wolfstitch()
        
        # Test with known text
        text = "test"  # 4 characters
        tokens = processor._estimate_tokens_char_based(text)
        
        # Should be 4 / 4 = 1
        assert tokens == 1
    
    def test_unknown_tokenizer_fallback(self):
        """Test fallback for unknown tokenizer"""
        processor = Wolfstitch()
        
        tokenizer_func = processor._get_tokenizer_function("unknown-tokenizer")
        
        # Should fallback to word-based
        text = "test text"
        tokens = tokenizer_func(text)
        assert tokens == 2  # 2 words * 1.3 = 2.6, rounded to 2


if __name__ == "__main__":
    pytest.main([__file__])