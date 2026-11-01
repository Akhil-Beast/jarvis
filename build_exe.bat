@echo off
title JARVIS Standalone Executable Builder
cd /d "%~dp0"

echo ===================================================
echo     Building Standalone JARVIS.exe via PyInstaller
echo ===================================================
echo.

if not exist "venv\Scripts\pyinstaller.exe" (
    echo [ERROR] PyInstaller not found in venv! Installing...
    venv\Scripts\pip.exe install pyinstaller
)

echo Packaging application...
venv\Scripts\pyinstaller.exe --noconsole --name "JARVIS" ^
    --icon "assets\icon_active.png" ^
    --add-data "assets;assets" ^
    --add-data "config;config" ^
    --hidden-import "comtypes" ^
    --hidden-import "uiautomation" ^
    --hidden-import "pyautogui" ^
    --hidden-import "pynput" ^
    --hidden-import "pyttsx3" ^
    --hidden-import "PySide6" ^
    --hidden-import "google.genai" ^
    main.py

echo.
echo ===================================================
echo   Build Complete! Standalone executable is at:
echo       dist\JARVIS\JARVIS.exe
echo ===================================================
echo.
pause
