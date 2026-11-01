@echo off
title JARVIS Environment Setup
cd /d "%~dp0"

echo ===================================================
echo     Installing Dependencies for JARVIS Assistant
echo ===================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH!
    echo Please install Python 3.10+ from python.org and check "Add to PATH".
    pause
    exit /b
)

if not exist "venv" (
    echo Creating virtual environment in .\venv...
    python -m venv venv
)

echo Upgrading pip and installing required packages...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\pip.exe install -r requirements.txt

echo.
echo ===================================================
echo   Setup Complete! You can now start JARVIS via:
echo       run.bat
echo ===================================================
echo.
pause
