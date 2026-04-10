@echo off
title MarvelAura2 - Emotion-Aware AI Companion
color 0A
setlocal EnableDelayedExpansion

echo ============================================
echo   MarvelAura2 - Emotion-Aware AI Companion
echo ============================================
echo.

:: 1. Find Python Executable
set "PYTHON_CMD="
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
) else (
    py --version >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_CMD=py"
    ) else (
        echo [ERROR] Python is not installed or not in PATH.
        echo Please install Python 3.9+ from https://python.org
        pause
        exit /b 1
    )
)
echo [SETUP] Using !PYTHON_CMD!

:: 2. Check .env file
if not exist ".env" (
    echo [WARNING] .env file not found!
    echo Copying .env.example to .env...
    copy .env.example .env >nul
    echo.
    echo [ACTION REQUIRED] Please edit .env and add your Gemini OR OpenAI API key!
    echo Opening .env in notepad...
    notepad .env
    pause
)

:: 3. Strict Virtual Environment Check
:: If 'venv' folder exists but is corrupted/empty (no activate.bat), delete it.
if exist "venv" (
    if not exist "venv\Scripts\activate.bat" (
        echo [WARNING] Corrupted venv detected. Removing and recreating...
        rmdir /S /Q venv
    )
)

if not exist "venv\Scripts\activate.bat" (
    echo [SETUP] Creating virtual environment...
    !PYTHON_CMD! -m venv venv
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment! Check your Python installation.
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
    echo.
)

:: 4. Activate VENV
echo [SETUP] Activating virtual environment...
call venv\Scripts\activate.bat
if !errorlevel! neq 0 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

:: 5. Install Dependencies (Verbose so user can see errors)
echo [SETUP] Installing/Updating dependencies (this may take a moment)...
pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo [ERROR] pip install failed! Please read the red error messages above.
    pause
    exit /b 1
)

:: 6. Start Server
echo.
echo ============================================
echo   Starting MarvelAura2 Server...
echo   Local Access:   http://localhost:8000
echo   Network Access: http://^<your-local-ip^>:8000
echo   Press Ctrl+C to stop
echo ============================================
echo.

cd /d "%~dp0"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 9000 --reload

pause
