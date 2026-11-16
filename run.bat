@echo off
title J.A.R.V.I.S. Desktop Assistant
cd /d "%~dp0"

echo ======================================================================
echo   J.A.R.V.I.S. // Autonomous Desktop Voice Assistant
echo   Mode: DESKTOP (Windows Native Automation)
echo   Hotkeys: Ctrl+Alt+Space (Toggle HUD) ^| Esc (Emergency Stop)
echo ======================================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not detected! Running setup.bat...
    call setup.bat
)

echo Starting JARVIS Desktop Assistant...
start "" "venv\Scripts\pythonw.exe" main.py
echo [OK] JARVIS is now running in the background and system tray.
echo      - Speak "Hey JARVIS" to command
echo      - Press Ctrl+Alt+Space to toggle HUD
echo      - Press Escape to emergency abort
echo.
timeout /t 3 >nul
