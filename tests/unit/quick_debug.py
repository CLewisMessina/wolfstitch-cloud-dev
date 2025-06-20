#!/usr/bin/env python3
"""
Quick debug script to find exactly which extension is failing
"""

from wolfcore.cleaner import detect_content_type

def debug_extensions():
    """Debug which extension is causing the test failure"""
    print("🔍 Debugging extension classification...")
    
    # Test each extension from the original failing test
    test_extensions = ['.csv', '.json', '.xml', '.xlsx', '.sqlite']
    
    for ext in test_extensions:
        result = detect_content_type(ext)
        expected = 'data' if ext != '.xml' else 'code'
        status = "✅" if result == expected else "❌"
        print(f"{ext} -> {result} (expected: {expected}) {status}")
    
    print("\n📋 Extension categories in cleaner.py:")
    
    # Show what's actually in each category
    from wolfcore.cleaner import DATA_EXTENSIONS, CODE_EXTENSIONS, DOCUMENT_EXTENSIONS
    
    print(f"DATA: {sorted(DATA_EXTENSIONS)}")
    print(f"CODE: {sorted(list(CODE_EXTENSIONS)[:10])}... (showing first 10)")
    print(f"DOCS: {sorted(DOCUMENT_EXTENSIONS)}")

if __name__ == "__main__":
    debug_extensions()
