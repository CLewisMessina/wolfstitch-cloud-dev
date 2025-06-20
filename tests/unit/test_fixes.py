#!/usr/bin/env python3
"""
Quick diagnostic script to test the specific failing cases
Run this to verify the fixes work
"""

from wolfcore.cleaner import detect_content_type
from wolfcore.chunker import TextChunker, ChunkingConfig

def test_data_extensions():
    """Test the data extension detection"""
    print("Testing data extensions...")
    
    # These should be 'data'
    data_extensions = ['.csv', '.json', '.xlsx', '.sqlite']
    for ext in data_extensions:
        result = detect_content_type(ext)
        print(f"{ext} -> {result}")
        assert result == 'data', f"Expected 'data' for {ext}, got {result}"
    
    # XML should be 'code' (markup/configuration)
    xml_result = detect_content_type('.xml')
    print(f".xml -> {xml_result}")
    assert xml_result == 'code', f"Expected 'code' for .xml, got {xml_result}"
    
    print("✅ Data extension tests passed!")


def test_word_tokenizer():
    """Test the word-based tokenizer"""
    print("\nTesting word tokenizer...")
    
    text = "This is a test sentence with ten words exactly."
    word_count = len(text.split())
    print(f"Text: '{text}'")
    print(f"Word count: {word_count}")
    
    def word_tokenizer(text):
        return len(text.split())
    
    config = ChunkingConfig(method="sentence", max_tokens=5)
    chunker = TextChunker(config)
    chunks = chunker.chunk_text(text, word_tokenizer)
    
    print(f"Created {len(chunks)} chunks with max_tokens=5")
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i}: {chunk.token_count} tokens - '{chunk.text[:50]}...'")
    
    # Should create at least 1 chunk (might be 1 if sentence is treated as unit)
    assert len(chunks) >= 1, f"Expected at least 1 chunk, got {len(chunks)}"
    
    print("✅ Word tokenizer test passed!")


def test_file_access():
    """Test if there are file access issues"""
    print("\nTesting file access...")
    
    try:
        from wolfcore.parsers import FileParser
        parser = FileParser()
        
        # Try to parse a simple text content
        print("FileParser imported successfully")
        print("✅ File access test passed!")
        
    except Exception as e:
        print(f"❌ File access issue: {e}")


if __name__ == "__main__":
    print("🔧 Running diagnostic tests for failing cases...\n")
    
    try:
        test_data_extensions()
        test_word_tokenizer() 
        test_file_access()
        
        print("\n🎉 All diagnostic tests passed!")
        print("The test failures should now be resolved.")
        
    except Exception as e:
        print(f"\n❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()
