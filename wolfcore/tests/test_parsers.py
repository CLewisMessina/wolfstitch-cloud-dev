"""
Wolfcore Parser Tests
Comprehensive test suite for file parsing functionality
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import io

from wolfcore.parsers import FileParser, ParsedFile, parse_file
from wolfcore.exceptions import ParsingError, UnsupportedFormatError


class TestFileParser:
    """Test suite for FileParser class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.parser = FileParser(max_file_size_mb=10)  # Small size for testing
        
    def teardown_method(self):
        """Clean up after tests"""
        self.parser._cleanup_temp_files()
    
    def test_supported_formats(self):
        """Test that supported formats are correctly defined"""
        formats = FileParser.get_supported_formats()
        
        # Check key formats are present
        assert 'pdf' in formats
        assert 'docx' in formats
        assert 'txt' in formats
        assert 'python' in formats
        assert 'javascript' in formats
        assert 'json' in formats
        
        # Check format detection
        assert FileParser.is_supported('document.pdf')
        assert FileParser.is_supported('script.py')
        assert FileParser.is_supported('data.json')
        assert not FileParser.is_supported('unknown.xyz')
    
    def test_detect_format(self):
        """Test format detection from filenames"""
        test_cases = [
            ('document.pdf', 'pdf'),
            ('script.py', 'python'),
            ('data.json', 'json'),
            ('style.css', None),  # Unsupported
            ('README.md', 'markdown'),
            ('config.yaml', 'yaml'),
            ('spreadsheet.xlsx', 'xlsx'),
        ]
        
        for filename, expected in test_cases:
            if expected:
                assert self.parser._detect_format(filename) == expected
            else:
                with pytest.raises(UnsupportedFormatError):
                    self.parser._detect_format(filename)
    
    def test_file_size_validation(self):
        """Test file size validation"""
        # Create a temporary file larger than limit
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            # Write more than 10MB (our test limit)
            large_content = 'x' * (11 * 1024 * 1024)
            f.write(large_content)
            temp_path = f.name
        
        try:
            with pytest.raises(ParsingError, match="File too large"):
                self.parser.parse(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_parse_text_file(self):
        """Test parsing plain text files"""
        content = "This is a test document.\nIt has multiple lines.\nAnd some content."
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            result = self.parser.parse(temp_path)
            
            assert isinstance(result, ParsedFile)
            assert result.text == content
            assert result.format == 'txt'
            assert result.filename == os.path.basename(temp_path)
            assert result.word_count == 11
            assert result.line_count == 3
            assert result.encoding is not None
            
        finally:
            os.unlink(temp_path)
    
    def test_parse_python_file(self):
        """Test parsing Python source code"""
        content = '''def hello_world():
    """Print hello world"""
    print("Hello, World!")
    
if __name__ == "__main__":
    hello_world()
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            result = self.parser.parse(temp_path)
            
            assert result.format == 'python'
            assert result.language == 'Python'
            assert 'def hello_world' in result.text
            assert result.metadata['is_code_file'] is True
            
        finally:
            os.unlink(temp_path)
    
    def test_parse_json_file(self):
        """Test parsing JSON files"""
        content = {
            "name": "Test Document",
            "data": [1, 2, 3],
            "nested": {"key": "value"}
        }
        
        import json
        json_content = json.dumps(content, indent=2)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(json_content)
            temp_path = f.name
        
        try:
            result = self.parser.parse(temp_path)
            
            assert result.format == 'json'
            assert 'Test Document' in result.text
            assert 'nested' in result.text
            
        finally:
            os.unlink(temp_path)
    
    def test_parse_file_object(self):
        """Test parsing from file-like objects"""
        content = "Test content from file object"
        file_obj = io.BytesIO(content.encode('utf-8'))
        
        result = self.parser.parse(file_obj, filename="test.txt")
        
        assert result.text == content
        assert result.filename == "test.txt"
        assert result.format == 'txt'
    
    def test_encoding_detection(self):
        """Test automatic encoding detection"""
        # Test UTF-8 content
        content = "Test with unicode: ñáéíóú 中文 🚀"
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
            f.write(content.encode('utf-8'))
            temp_path = f.name
        
        try:
            result = self.parser.parse(temp_path)
            assert content in result.text
            assert result.encoding == 'utf-8'
            
        finally:
            os.unlink(temp_path)
    
    def test_parse_nonexistent_file(self):
        """Test handling of nonexistent files"""
        with pytest.raises(ParsingError, match="File not found"):
            self.parser.parse("nonexistent_file.txt")
    
    @patch('wolfcore.parsers.extract_text')
    def test_parse_pdf_mock(self, mock_extract):
        """Test PDF parsing with mocked pdfminer"""
        mock_extract.return_value = "Extracted PDF content"
        
        # Create empty temp file for path validation
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_path = f.name
        
        try:
            with patch('wolfcore.parsers.PDFPage') as mock_pdfpage:
                mock_pdfpage.get_pages.return_value = [1, 2, 3]  # 3 pages
                
                result = self.parser.parse(temp_path)
                
                assert result.text == "Extracted PDF content"
                assert result.format == 'pdf'
                assert result.extraction_method == 'pdfminer.six'
                assert result.metadata['page_count'] == 3
                
        finally:
            os.unlink(temp_path)
    
    def test_parse_csv_content(self):
        """Test CSV content parsing"""
        csv_content = """Name,Age,City
John,25,New York
Jane,30,San Francisco
Bob,35,Chicago"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            result = self.parser.parse(temp_path)
            
            assert result.format == 'csv'
            assert 'Name | Age | City' in result.text
            assert 'John | 25 | New York' in result.text
            assert 'Jane | 30 | San Francisco' in result.text
            
        finally:
            os.unlink(temp_path)
    
    def test_language_detection(self):
        """Test programming language detection"""
        test_cases = [
            ('python', 'Python'),
            ('javascript', 'JavaScript'),
            ('java', 'Java'),
            ('cpp', 'C++'),
            ('go', 'Go'),
            ('rust', 'Rust'),
            ('txt', None),
        ]
        
        for file_format, expected_language in test_cases:
            result = self.parser._detect_language(file_format, "sample code")
            assert result == expected_language
    
    def test_cleanup_temp_files(self):
        """Test temporary file cleanup"""
        # Create a temp file and add to parser's tracking
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = Path(f.name)
        
        self.parser.temp_files.append(temp_path)
        assert temp_path.exists()
        
        # Cleanup should remove the file
        self.parser._cleanup_temp_files()
        assert not temp_path.exists()
        assert len(self.parser.temp_files) == 0


class TestParsedFile:
    """Test suite for ParsedFile data class"""
    
    def test_parsed_file_creation(self):
        """Test ParsedFile creation and post-init calculations"""
        text = "This is a test document with multiple words.\nIt has two lines."
        
        parsed = ParsedFile(
            text=text,
            filename="test.txt",
            format="txt"
        )
        
        assert parsed.text == text
        assert parsed.filename == "test.txt"
        assert parsed.format == "txt"
        assert parsed.word_count == 12  # Calculated in __post_init__
        assert parsed.line_count == 2   # Calculated in __post_init__
    
    def test_parsed_file_empty_text(self):
        """Test ParsedFile with empty text"""
        parsed = ParsedFile(
            text="",
            filename="empty.txt", 
            format="txt"
        )
        
        assert parsed.word_count == 0
        assert parsed.line_count == 1  # Empty text still has 1 line
    
    def test_parsed_file_with_metadata(self):
        """Test ParsedFile with custom metadata"""
        metadata = {
            "author": "Test Author",
            "created": "2024-01-01",
            "custom_field": "custom_value"
        }
        
        parsed = ParsedFile(
            text="Sample text",
            filename="sample.txt",
            format="txt",
            metadata=metadata
        )
        
        assert parsed.metadata == metadata
        assert parsed.metadata["author"] == "Test Author"


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_parse_file_function(self):
        """Test the parse_file convenience function"""
        content = "Test content for convenience function"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            result = parse_file(temp_path)
            
            assert isinstance(result, ParsedFile)
            assert result.text == content
            assert result.format == 'txt'
            
        finally:
            os.unlink(temp_path)
    
    def test_get_supported_formats_function(self):
        """Test get_supported_formats convenience function"""
        from wolfcore.parsers import get_supported_formats
        
        formats = get_supported_formats()
        assert isinstance(formats, list)
        assert 'pdf' in formats
        assert 'txt' in formats
        assert len(formats) > 10  # Should have many formats
    
    def test_is_supported_format_function(self):
        """Test is_supported_format convenience function"""
        from wolfcore.parsers import is_supported_format
        
        assert is_supported_format('document.pdf') is True
        assert is_supported_format('script.py') is True
        assert is_supported_format('unknown.xyz') is False


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def setup_method(self):
        self.parser = FileParser()
    
    def test_unsupported_format_error(self):
        """Test UnsupportedFormatError is raised for unknown formats"""
        with pytest.raises(UnsupportedFormatError):
            self.parser._detect_format("unknown.xyz")
    
    def test_parsing_error_propagation(self):
        """Test that parsing errors are properly propagated"""
        # Create a file that will cause parsing issues
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
            f.write(b"Not a real PDF file")
            temp_path = f.name
        
        try:
            # This should raise a ParsingError when pdfminer fails
            with pytest.raises(ParsingError):
                self.parser.parse(temp_path)
                
        finally:
            os.unlink(temp_path)
    
    def test_encoding_fallback(self):
        """Test encoding detection fallback mechanisms"""
        # Create file with problematic encoding
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
            # Write some bytes that might cause encoding issues
            f.write(b'\xff\xfe\x00\x00invalid utf-8 \x80\x81\x82')
            temp_path = f.name
        
        try:
            result = self.parser.parse(temp_path)
            
            # Should not raise exception, should use fallback encoding
            assert result is not None
            assert len(result.warnings) > 0  # Should have encoding warnings
            
        finally:
            os.unlink(temp_path)


class TestIntegration:
    """Integration tests for parser functionality"""
    
    def test_multiple_file_processing(self):
        """Test processing multiple files of different formats"""
        files_to_test = [
            ("test.txt", "This is a text file."),
            ("test.py", "def hello():\n    print('Hello World')"),
            ("test.json", '{"name": "test", "value": 123}'),
            ("test.md", "# Header\n\nThis is markdown content."),
        ]
        
        parser = FileParser()
        results = []
        temp_files = []
        
        try:
            # Create temporary files
            for filename, content in files_to_test:
                with tempfile.NamedTemporaryFile(mode='w', suffix=f".{filename.split('.')[-1]}", delete=False) as f:
                    f.write(content)
                    temp_files.append(f.name)
            
            # Parse all files
            for temp_path, (original_name, expected_content) in zip(temp_files, files_to_test):
                result = parser.parse(temp_path)
                results.append(result)
                
                # Basic validation
                assert result.text is not None
                assert len(result.text) > 0
                assert result.format is not None
                assert result.processing_time >= 0
            
            # Check we got results for all files
            assert len(results) == len(files_to_test)
            
            # Check format detection worked correctly
            expected_formats = ['txt', 'python', 'json', 'markdown']
            actual_formats = [r.format for r in results]
            assert actual_formats == expected_formats
            
        finally:
            # Cleanup
            for temp_path in temp_files:
                try:
                    os.unlink(temp_path)
                except:
                    pass


# Performance and stress tests
class TestPerformance:
    """Performance and stress tests"""
    
    def test_large_text_file_performance(self):
        """Test performance with large text files"""
        # Create a moderately large text file (1MB)
        large_content = "This is a line of text.\n" * 50000  # ~1MB
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(large_content)
            temp_path = f.name
        
        try:
            parser = FileParser(max_file_size_mb=10)
            result = parser.parse(temp_path)
            
            # Should complete in reasonable time (< 5 seconds for 1MB)
            assert result.processing_time < 5.0
            assert result.text == large_content
            assert result.word_count > 100000  # Should have lots of words
            
        finally:
            os.unlink(temp_path)
    
    def test_memory_usage_with_multiple_files(self):
        """Test memory doesn't grow excessively with multiple file parsing"""
        import gc
        
        parser = FileParser()
        
        # Process multiple files and ensure cleanup
        for i in range(10):
            content = f"Test file {i} with some content to parse."
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(content)
                temp_path = f.name
            
            try:
                result = parser.parse(temp_path)
                assert result.text == content
                
                # Force garbage collection
                del result
                gc.collect()
                
            finally:
                os.unlink(temp_path)
        
        # Ensure temp files are cleaned up
        assert len(parser.temp_files) == 0


if __name__ == "__main__":
    pytest.main([__file__])