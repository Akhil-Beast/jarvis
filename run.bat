@echo off
title J.A.R.V.I.S. Desktop Assistant
cd /d "%~dp0"

echo ======================================================================
echo   J.A.R.V.I.S. // Autonomous Desktop Assistant (Web HUD Mode)
echo   - Mode: DESKTOP (Windows Native Automation)
echo   - UI: Modern Web HUD (100% Identical to Cloud Render)
echo   - Local URL: http://localhost:10000
echo   - Hotkeys: Ctrl+Alt+Space (Toggle HUD) ^| Esc (Emergency Stop)
echo ======================================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not detected! Running setup.bat...
    call setup.bat
)

echo Starting JARVIS Desktop Assistant...
"venv\Scripts\python.exe" main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo JARVIS exited with code %ERRORLEVEL%.
    pause
)
