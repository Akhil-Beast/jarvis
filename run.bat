@echo off
title JARVIS Voice Assistant Launcher
cd /d "%~dp0"

echo ===================================================
echo       J.A.R.V.I.S. Windows Desktop Assistant
echo ===================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not detected!
    echo Running setup.bat first...
    call setup.bat
)

echo Starting JARVIS Desktop HUD...
start "" "venv\Scripts\pythonw.exe" main.py
echo JARVIS is running in the background and system tray.
echo Press Ctrl+Alt+Space to toggle active listening.
echo Press Escape to emergency abort any automation.
echo.
exit
