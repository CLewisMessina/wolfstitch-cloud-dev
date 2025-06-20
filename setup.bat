@echo off
echo 🐺 Wolfstitch Cloud - Windows Development Setup
echo ===============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.8+ first.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python found
python --version

REM Create virtual environment
echo.
echo 📦 Creating virtual environment...
if exist venv (
    echo ✅ Virtual environment already exists
) else (
    python -m venv venv
    echo ✅ Virtual environment created
)

REM Activate virtual environment
echo.
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo 📈 Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo.
echo 📚 Installing dependencies...
pip install -r requirements.txt

REM Install in development mode
echo.
echo 🔨 Installing package in development mode...
pip install -e .

REM Create environment file
echo.
echo ⚙️ Setting up environment configuration...
if exist .env (
    echo ✅ Environment file already exists
) else (
    copy .env.example .env
    echo ✅ Environment file created from template
)

REM Create directories
echo.
echo 📁 Creating required directories...
if not exist uploads mkdir uploads
if not exist temp mkdir temp
if not exist logs mkdir logs
if not exist exports mkdir exports
if not exist test-files mkdir test-files
echo ✅ Directories created

REM Create test files
echo.
echo 📝 Creating test files...

REM Create sample text file
echo This is a sample text file for testing Wolfstitch Cloud.> test-files\sample.txt
echo.>> test-files\sample.txt
echo It contains multiple paragraphs with different content types.>> test-files\sample.txt
echo This helps test the text processing and chunking functionality.>> test-files\sample.txt
echo.>> test-files\sample.txt
echo Features to test:>> test-files\sample.txt
echo - Text extraction>> test-files\sample.txt
echo - Paragraph splitting>> test-files\sample.txt
echo - Token counting>> test-files\sample.txt
echo - Metadata extraction>> test-files\sample.txt
echo.>> test-files\sample.txt
echo The quick brown fox jumps over the lazy dog.>> test-files\sample.txt

REM Create sample Python file
echo """Sample Python file for testing code processing""">> test-files\sample.py
echo.>> test-files\sample.py
echo def hello_world():>> test-files\sample.py
echo     """Print a greeting message""">> test-files\sample.py
echo     print("Hello, World!")>> test-files\sample.py
echo     return "Hello, World!">> test-files\sample.py
echo.>> test-files\sample.py
echo if __name__ == "__main__":>> test-files\sample.py
echo     hello_world()>> test-files\sample.py

REM Create sample JSON file
echo {>> test-files\sample.json
echo   "name": "Wolfstitch Test Data",>> test-files\sample.json
echo   "description": "Sample JSON file for testing",>> test-files\sample.json
echo   "version": "1.0.0",>> test-files\sample.json
echo   "features": ["JSON parsing", "Data extraction"]>> test-files\sample.json
echo }>> test-files\sample.json

echo ✅ Test files created

REM Check Redis
echo.
echo 🔍 Checking Redis...
tasklist /FI "IMAGENAME eq redis-server.exe" 2>NUL | find /I /N "redis-server.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo ✅ Redis is running
) else (
    echo ⚠️ Redis not running. Please:
    echo 1. Download Redis from: https://github.com/tporadowski/redis/releases
    echo 2. Extract to C:\Redis
    echo 3. Run: C:\Redis\redis-server.exe
    echo.
    echo The app will work without Redis but with limited functionality.
)

REM Run tests
echo.
echo 🧪 Running basic tests...
python -m pytest wolfcore\tests\ -v
if errorlevel 1 (
    echo ⚠️ Some tests failed, but setup can continue
) else (
    echo ✅ All tests passed
)

echo.
echo 🎉 Setup complete!
echo.
echo Next steps:
echo 1. Make sure Redis is running (optional for basic functionality)
echo 2. Start the development server:
echo    venv\Scripts\activate
echo    uvicorn backend.main:app --reload
echo 3. Open http://localhost:8000/docs in your browser
echo 4. Try the quick-process endpoint with test files
echo.
echo Useful commands:
echo   📖 API Docs: http://localhost:8000/docs
echo   🔍 Health Check: http://localhost:8000/health
echo   ⚡ Quick Process: http://localhost:8000/api/v1/processing/quick-process
echo.
pause