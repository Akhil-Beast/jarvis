@echo off
title J.A.R.V.I.S. Web HUD Server
cd /d "%~dp0"

echo ======================================================================
echo   J.A.R.V.I.S. // Local Web HUD Server
echo   URL: http://localhost:10000
echo ======================================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not detected! Running setup.bat...
    call setup.bat
)

echo Opening Web HUD in browser...
start "" "http://localhost:10000"
echo Starting local FastAPI server on port 10000...
venv\Scripts\python.exe server.py
