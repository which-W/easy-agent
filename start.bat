@echo off
echo ========================================
echo Easy-Agent Setup and Start Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Python detected successfully
echo.

REM Check if virtual environment exists
if not exist venv (
    echo [2/4] Creating Python virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        pause
        exit /b 1
    )
) else (
    echo [2/4] Virtual environment already exists
)
echo.

REM Activate virtual environment
echo [3/4] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)
echo.

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)
echo.

REM Check if .env file exists
if not exist .env (
    echo [!] WARNING: .env file not found
    echo Please copy .env.example to .env and set your DASHSCOPE_API_KEY
    echo.
    echo Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo Please edit .env and set your API key before starting the server.
    echo.
    pause
)

echo.
echo ========================================
echo [4/4] Starting Easy-Agent Server...
echo ========================================
echo.
echo Server will be available at:
echo - API: http://localhost:8000
echo - API Docs: http://localhost:8000/docs
echo - Frontend: Open frontend/index.html in your browser
echo.
echo Press Ctrl+C to stop the server
echo.

cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause
