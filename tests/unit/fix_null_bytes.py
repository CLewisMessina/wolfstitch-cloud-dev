#!/usr/bin/env python3
"""
Fix null bytes in Python files that are causing import errors
"""

import os
import sys
from pathlib import Path

def check_file_for_null_bytes(file_path):
    """Check if a file contains null bytes"""
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            if b'\x00' in content:
                return True, content
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return False, None

def fix_null_bytes_in_file(file_path, content):
    """Remove null bytes from file content"""
    try:
        # Remove null bytes
        cleaned_content = content.replace(b'\x00', b'')
        
        # Write back the cleaned content
        with open(file_path, 'wb') as f:
            f.write(cleaned_content)
        
        print(f"✅ Fixed null bytes in: {file_path}")
        return True
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

def scan_python_files():
    """Scan all Python files for null bytes"""
    
    python_files = []
    
    # Get all Python files in backend and wolfcore
    for directory in ['backend', 'wolfcore']:
        if Path(directory).exists():
            for py_file in Path(directory).rglob('*.py'):
                python_files.append(py_file)
    
    print(f"🔍 Scanning {len(python_files)} Python files for null bytes...")
    
    corrupted_files = []
    
    for py_file in python_files:
        has_null, content = check_file_for_null_bytes(py_file)
        if has_null:
            print(f"❌ Found null bytes in: {py_file}")
            corrupted_files.append((py_file, content))
        else:
            print(f"✅ Clean: {py_file}")
    
    return corrupted_files

def main():
    print("🔧 Null Bytes Detector and Fixer")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("backend").exists():
        print("❌ Error: Run this from the wolfstitch-cloud root directory")
        return
    
    # Scan for corrupted files
    corrupted_files = scan_python_files()
    
    if not corrupted_files:
        print("\n🎉 No null bytes found in Python files!")
        print("The error might be caused by something else.")
        print("\nTry these steps:")
        print("1. Check your .env file for binary content")
        print("2. Recreate any recently copied files")
        print("3. Check file permissions")
        return
    
    print(f"\n🚨 Found {len(corrupted_files)} corrupted files!")
    
    # Ask user if they want to fix them
    response = input("Do you want to fix these files? (y/n): ").lower().strip()
    
    if response == 'y':
        fixed_count = 0
        for file_path, content in corrupted_files:
            if fix_null_bytes_in_file(file_path, content):
                fixed_count += 1
        
        print(f"\n🎉 Fixed {fixed_count} out of {len(corrupted_files)} files!")
        print("\nNow try running: uvicorn backend.main:app --reload")
    else:
        print("\nSkipping file fixes.")
        print("You'll need to manually recreate these files:")
        for file_path, _ in corrupted_files:
            print(f"  - {file_path}")

if __name__ == "__main__":
    main()