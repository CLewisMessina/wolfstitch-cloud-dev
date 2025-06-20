#!/usr/bin/env python3
"""
Railway Setup Script for Wolfstitch Cloud
Validates configuration and dependencies for successful deployment
"""

import os
import sys
import subprocess
import importlib.util

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version < (3, 8):
        print(f"❌ Python {version.major}.{version.minor} is not supported. Minimum: Python 3.8")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def check_file_exists(filepath, description):
    """Check if required file exists"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ Missing {description}: {filepath}")
        return False

def check_directory_structure():
    """Validate project directory structure"""
    print("\n🔍 Checking directory structure...")
    
    required_files = [
        ("requirements.txt", "Dependencies file"),
        ("backend/main.py", "Main application file"),
        ("backend/__init__.py", "Backend package init"),
    ]
    
    optional_files = [
        ("backend/config.py", "Configuration file"),
        ("wolfcore/__init__.py", "Wolfcore package"),
        ("Dockerfile", "Docker configuration"),
        ("nixpacks.toml", "Nixpacks configuration"),
        ("Procfile", "Process configuration"),
    ]
    
    all_good = True
    
    # Check required files
    for filepath, description in required_files:
        if not check_file_exists(filepath, description):
            all_good = False
    
    # Check optional files
    print("\n📋 Optional files:")
    for filepath, description in optional_files:
        check_file_exists(filepath, description)
    
    return all_good

def check_dependencies():
    """Check if key dependencies can be imported"""
    print("\n🔍 Checking dependencies...")
    
    critical_deps = [
        ("fastapi", "FastAPI framework"),
        ("uvicorn", "ASGI server"),
        ("pydantic", "Data validation"),
    ]
    
    optional_deps = [
        ("wolfcore", "Wolfcore library"),
        ("psycopg2", "PostgreSQL adapter"),
        ("redis", "Redis client"),
    ]
    
    all_critical_ok = True
    
    # Check critical dependencies
    for module_name, description in critical_deps:
        try:
            importlib.import_module(module_name)
            print(f"✅ {description}: {module_name}")
        except ImportError:
            print(f"❌ Missing {description}: {module_name}")
            all_critical_ok = False
    
    # Check optional dependencies
    print("\n📋 Optional dependencies:")
    for module_name, description in optional_deps:
        try:
            importlib.import_module(module_name)
            print(f"✅ {description}: {module_name}")
        except ImportError:
            print(f"⚠️ Optional {description}: {module_name} (not found)")
    
    return all_critical_ok

def check_environment_variables():
    """Check Railway environment variables"""
    print("\n🔍 Checking environment variables...")
    
    required_env_vars = []  # None required for basic operation
    optional_env_vars = [
        ("PORT", "Server port"),
        ("ENVIRONMENT", "Environment setting"),
        ("DATABASE_URL", "Database connection"),
        ("REDIS_URL", "Redis connection"),
        ("SECRET_KEY", "Application secret"),
    ]
    
    all_good = True
    
    # Check required env vars
    for var_name, description in required_env_vars:
        if os.getenv(var_name):
            print(f"✅ {description}: {var_name}")
        else:
            print(f"❌ Missing {description}: {var_name}")
            all_good = False
    
    # Check optional env vars
    print("📋 Optional environment variables:")
    for var_name, description in optional_env_vars:
        value = os.getenv(var_name)
        if value:
            # Mask sensitive values
            if "secret" in var_name.lower() or "key" in var_name.lower():
                display_value = "***" + value[-4:] if len(value) > 4 else "***"
            else:
                display_value = value
            print(f"✅ {description}: {var_name}={display_value}")
        else:
            print(f"⚠️ Optional {description}: {var_name} (not set)")
    
    return all_good

def create_missing_files():
    """Create missing __init__.py files"""
    print("\n🔧 Creating missing __init__.py files...")
    
    init_files = [
        "backend/__init__.py",
        "wolfcore/__init__.py",
    ]
    
    for init_file in init_files:
        if not os.path.exists(init_file):
            os.makedirs(os.path.dirname(init_file), exist_ok=True)
            with open(init_file, 'w') as f:
                f.write(f'"""Package: {os.path.dirname(init_file).replace("/", ".")}"""\n')
            print(f"✅ Created: {init_file}")
        else:
            print(f"✅ Exists: {init_file}")

def run_test_import():
    """Test importing the main application"""
    print("\n🧪 Testing application import...")
    
    try:
        # Add current directory to Python path
        if os.getcwd() not in sys.path:
            sys.path.insert(0, os.getcwd())
        
        # Try to import the main application
        spec = importlib.util.spec_from_file_location("main", "backend/main.py")
        if spec and spec.loader:
            main_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(main_module)
            print("✅ Main application imports successfully")
            return True
        else:
            print("❌ Failed to load main application spec")
            return False
            
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def main():
    """Run all checks"""
    print("🚀 Railway Deployment Readiness Check for Wolfstitch Cloud\n")
    
    checks = [
        ("Python Version", check_python_version),
        ("Directory Structure", check_directory_structure),
        ("Dependencies", check_dependencies),
        ("Environment Variables", check_environment_variables),
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"\n{'='*50}")
        print(f"🔍 {check_name}")
        print('='*50)
        
        if not check_func():
            all_passed = False
    
    # Create missing files
    print(f"\n{'='*50}")
    print("🔧 File Creation")
    print('='*50)
    create_missing_files()
    
    # Test import
    print(f"\n{'='*50}")
    print("🧪 Import Test")
    print('='*50)
    import_ok = run_test_import()
    
    # Final summary
    print(f"\n{'='*50}")
    print("📊 SUMMARY")
    print('='*50)
    
    if all_passed and import_ok:
        print("✅ ALL CHECKS PASSED - Ready for Railway deployment!")
        print("\n🚀 Next steps:")
        print("1. Commit your changes to Git")
        print("2. Push to your Railway-connected repository")
        print("3. Check Railway build logs")
        print("4. Test your deployed API at https://api.wolfstitch.dev")
    else:
        print("❌ SOME CHECKS FAILED - Please fix issues before deploying")
        print("\n🔧 Common fixes:")
        print("1. Install missing dependencies: pip install -r requirements.txt")
        print("2. Check file paths and naming")
        print("3. Verify environment configuration")
    
    return all_passed and import_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)