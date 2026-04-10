@echo off
title MarvelAura2 - Frontend Server (Port 3000)
color 0B
setlocal

echo ============================================
echo   MarvelAura2 - Emotion-Aware AI Companion
echo   [Frontend Server]
echo ============================================
echo.
echo Make sure you are also running start.bat (or https_start.bat) 
echo so the backend is available!
echo.
echo   Local Access:   http://localhost:3000
echo   Network Access: http://^<your-local-ip^>:3000
echo   Press Ctrl+C to stop
echo ============================================
echo.

cd /d "%~dp0\frontend"
python -m http.server 3000

pause