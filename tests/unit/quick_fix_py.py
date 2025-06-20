#!/usr/bin/env python3
"""
Quick fix script to create all missing files for Wolfstitch Cloud
Run this if you're getting import errors
"""

import os
from pathlib import Path

def create_file(path, content):
    """Create a file with given content"""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not file_path.exists():
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Created: {path}")
        return True
    else:
        print(f"⚠️ Already exists: {path}")
        return False

def main():
    print("🔧 Quick Fix - Creating Missing Files")
    print("=" * 40)
    
    # Create basic __init__.py files
    init_files = [
        "backend/__init__.py",
        "backend/models/__init__.py", 
        "backend/api/__init__.py",
        "backend/services/__init__.py",
        "wolfcore/tests/__init__.py"
    ]
    
    for init_file in init_files:
        create_file(init_file, f'"""Package: {init_file.replace("/__init__.py", "").replace("/", ".")}"""')
    
    # Create directory keeper files
    directories = ["uploads", "temp", "logs", "exports", "test-files"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        create_file(f"{directory}/.gitkeep", "# Keep this directory in git\n")
    
    # Check if critical files exist
    critical_files = [
        "backend/database.py",
        "backend/config.py", 
        "backend/dependencies.py",
        "backend/models/schemas.py",
        "wolfcore/__init__.py",
        "wolfcore/parsers.py"
    ]
    
    missing_critical = []
    for file in critical_files:
        if not Path(file).exists():
            missing_critical.append(file)
    
    if missing_critical:
        print(f"\n❌ Still missing {len(missing_critical)} critical files:")
        for file in missing_critical:
            print(f"   - {file}")
        print("\nYou need to create these files manually or from the artifacts.")
    else:
        print("\n🎉 All basic structure files created!")
        print("Try running: uvicorn backend.main:app --reload")

if __name__ == "__main__":
    main()