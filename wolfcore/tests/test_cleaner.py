"""
Tests for wolfcore.cleaner module
"""

import pytest
import asyncio
from wolfcore.cleaner import (
    clean_text, clean_text_async, detect_content_type,
    clean_code_content, clean_document_content, clean_data_content
)


class TestContentTypeDetection:
    """Test content type detection from file extensions"""
    
    def test_code_extensions(self):
        """Test code file extension detection"""
        code_extensions = ['.py', '.js', '.java', '.cpp', '.go', '.rs', '.html', '.css']
        for ext in code_extensions:
            assert detect_content_type(ext) == 'code'
    
    def test_document_extensions(self):
        """Test document file extension detection"""
        doc_extensions = ['.pdf', '.docx', '.txt', '.md', '.epub']
        for ext in doc_extensions:
            assert detect_content_type(ext) == 'document'
    
    def test_data_extensions(self):
        """Test data file extension detection"""
        # FIXED: Removed .xml (it's a code/markup extension)
        data_extensions = ['.csv', '.json', '.xlsx', '.sqlite']
        for ext in data_extensions:
            result = detect_content_type(ext)
            assert result == 'data', f"Expected 'data' for {ext}, got '{result}'"
    
    def test_unknown_extension(self):
        """Test unknown extensions default to document"""
        assert detect_content_type('.unknown') == 'document'
        assert detect_content_type('.xyz') == 'document'


class TestCodeCleaning:
    """Test code content cleaning"""
    
    def test_preserve_indentation(self):
        """Test that code indentation is preserved"""
        code = """def hello():
    print("Hello")
    if True:
        print("World")"""
        
        cleaned = clean_code_content(code)
        lines = cleaned.split('\n')
        
        assert lines[1].startswith('    ')  # 4 spaces preserved
        assert lines[3].startswith('        ')  # 8 spaces preserved
    
    def test_remove_trailing_whitespace(self):
        """Test removal of trailing whitespace"""
        code = "def hello():   \n    print('hello')  \n"
        cleaned = clean_code_content(code)
        
        lines = cleaned.split('\n')
        assert not lines[0].endswith(' ')
        assert not lines[1].endswith(' ')
    
    def test_aggressive_blank_line_removal(self):
        """Test aggressive blank line management"""
        code = """def func1():
    pass


def func2():
    pass



def func3():
    pass"""
        
        cleaned = clean_code_content(code)
        
        # Should have very few blank lines
        blank_lines = cleaned.count('\n\n')
        assert blank_lines <= 2  # Maximum 2 blank sections
    
    def test_empty_code(self):
        """Test handling of empty code"""
        assert clean_code_content("") == ""
        assert clean_code_content("   ") == ""


class TestDocumentCleaning:
    """Test document content cleaning"""
    
    def test_header_removal(self):
        """Test removal of common headers"""
        doc = """*** START OF PROJECT GUTENBERG EBOOK ***
This is the actual content.
*** END OF PROJECT GUTENBERG EBOOK ***"""
        
        cleaned = clean_document_content(doc, remove_headers=True)
        assert "PROJECT GUTENBERG" not in cleaned
        assert "This is the actual content." in cleaned
    
    def test_bullet_removal(self):
        """Test removal of bullet points"""
        doc = """Main content:
• First bullet
- Second bullet
* Third bullet
1. Numbered item"""
        
        cleaned = clean_document_content(doc, strip_bullets=True)
        assert "•" not in cleaned
        assert "First bullet" in cleaned
        assert "1." not in cleaned
    
    def test_whitespace_normalization(self):
        """Test whitespace normalization"""
        doc = """This   has    multiple    spaces.
This line
wraps.


Too many
newlines."""
        
        cleaned = clean_document_content(doc, normalize_whitespace=True)
        
        # Multiple spaces should be single
        assert "multiple    spaces" not in cleaned
        assert "multiple spaces" in cleaned
        
        # Wrapped lines should join
        assert "This line wraps." in cleaned
    
    def test_preserve_paragraphs(self):
        """Test that paragraph breaks are preserved"""
        doc = """First paragraph.

Second paragraph."""
        
        cleaned = clean_document_content(doc, normalize_whitespace=True)
        assert "\n\n" in cleaned  # Paragraph break preserved


class TestDataCleaning:
    """Test data content cleaning"""
    
    def test_minimal_cleaning(self):
        """Test that data cleaning is minimal"""
        data = """header1,header2,header3
value1,value2,value3
value4,value5,value6"""
        
        cleaned = clean_data_content(data)
        
        # Structure should be mostly preserved
        assert "header1,header2,header3" in cleaned
        assert cleaned.count(',') == data.count(',')
    
    def test_trailing_whitespace_removal(self):
        """Test removal of trailing whitespace only"""
        data = "header1,header2   \nvalue1,value2  \n"
        cleaned = clean_data_content(data)
        
        lines = cleaned.split('\n')
        assert not lines[0].endswith(' ')
        assert not lines[1].endswith(' ')


class TestMainCleaningFunction:
    """Test the main clean_text function"""
    
    def test_auto_detect_code(self):
        """Test automatic code detection and cleaning"""
        code = """def hello():
    print("hello")   


def world():
    print("world")"""
        
        cleaned = clean_text(code, file_extension='.py')
        
        # Should preserve indentation but reduce blank lines
        assert '    print("hello")' in cleaned
        assert cleaned.count('\n\n\n') == 0  # No triple newlines
    
    def test_auto_detect_document(self):
        """Test automatic document detection and cleaning"""
        doc = """This is a document.
• With bullets
And multiple   spaces."""
        
        cleaned = clean_text(doc, file_extension='.pdf')
        
        # Should normalize whitespace and remove bullets
        assert "multiple spaces" in cleaned
        assert "•" not in cleaned
    
    def test_manual_content_type(self):
        """Test manual content type override"""
        text = "Some text content"
        
        # Should use document cleaning even with code extension
        cleaned = clean_text(text, file_extension='.py', content_type='document')
        # Just verify it doesn't crash with this override
        assert isinstance(cleaned, str)
    
    def test_backward_compatibility(self):
        """Test backward compatibility without file extension"""
        doc = """Document   with   spaces.
• And bullets"""
        
        cleaned = clean_text(doc, remove_headers=True, normalize_whitespace=True, strip_bullets=True)
        
        # Should default to document cleaning
        assert "with spaces" in cleaned
        assert "•" not in cleaned
    
    def test_empty_text(self):
        """Test handling of empty text"""
        assert clean_text("") == ""
        assert clean_text(None) == None


class TestAsyncCleaning:
    """Test async cleaning functions"""
    
    @pytest.mark.asyncio
    async def test_async_cleaning(self):
        """Test async text cleaning"""
        text = "Test text   with   spaces."
        cleaned = await clean_text_async(text, file_extension='.txt')
        
        assert "with spaces" in cleaned
        assert isinstance(cleaned, str)
    
    @pytest.mark.asyncio
    async def test_async_code_cleaning(self):
        """Test async code cleaning"""
        code = """def test():
    pass   


def another():
    pass"""
        
        cleaned = await clean_text_async(code, file_extension='.py')
        
        # Should preserve code structure
        assert 'def test():' in cleaned
        assert '    pass' in cleaned


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_very_long_text(self):
        """Test cleaning of very long text"""
        long_text = "A" * 100000 + "\n\n\n" + "B" * 100000
        cleaned = clean_text(long_text, file_extension='.txt')
        
        # Should complete without error
        assert isinstance(cleaned, str)
        assert len(cleaned) > 0
    
    def test_unicode_content(self):
        """Test handling of unicode content"""
        unicode_text = "Hello 世界 🌍 café naïve résumé"
        cleaned = clean_text(unicode_text, file_extension='.txt')
        
        # Unicode should be preserved
        assert "世界" in cleaned
        assert "🌍" in cleaned
        assert "café" in cleaned
    
    def test_mixed_line_endings(self):
        """Test handling of mixed line endings"""
        mixed_text = "Line 1\nLine 2\r\nLine 3\rLine 4"
        cleaned = clean_text(mixed_text, file_extension='.txt')
        
        # Should handle gracefully
        assert isinstance(cleaned, str)
        assert "Line 1" in cleaned


if __name__ == "__main__":
    pytest.main([__file__])
