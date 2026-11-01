# J.A.R.V.I.S. // AI-Powered Windows Voice Control Assistant

A local, modular, and extensible desktop voice assistant designed for **Windows 10 and Windows 11**. JARVIS allows hands-free voice control across your entire PC, bridging speech recognition, AI reasoning, and multi-tiered Windows desktop automation.

---

## 1. System Architecture

```
                    +--------------------------------+
                    |  Voice Input / Wake Word       |
                    |  "Hey Assistant" / "Jarvis"    |
                    +--------------------------------+
                                   |
                                   v
                    +--------------------------------+
                    |  Speech-to-Text & AI Brain     |
                    |  (Fast Rules + Gemini / LLM)   |
                    +--------------------------------+
                                   |
                                   v
                    +--------------------------------+
                    |  Windows Automation Engine     |
                    |  (UI Automation + Win32 + Input|
                    +--------------------------------+
                               /      \
                              /        \
                             v          v
              +-------------------+   +--------------------+
              | Desktop Apps      |   | Windows OS         |
              | SolidWorks, CAD,  |   | File Explorer,     |
              | Chrome, Notepad   |   | Volume, Windows    |
              +-------------------+   +--------------------+
```

### Multi-Tier Automation Strategy
As highlighted in the architecture, no single technology can interact with every Windows program (e.g., legacy Win32, WPF, UWP modern apps, and CAD OpenGL viewports like SolidWorks and AutoCAD). JARVIS employs a multi-tiered fallback:
1. **Tier 1 (UI Automation):** Inspects the native UI accessibility tree (`uiautomation`) to click buttons, menu bars, and text fields by semantic name and automation ID.
2. **Tier 2 (Win32 API):** Interacts with window handles (`HWND`), brings background windows to foreground, and manages process lifecycles.
3. **Tier 3 (Keyboard & Mouse):** Clipboard-accelerated text typing (`pyperclip` + `pyautogui`), scrolling, and global key combinations.
4. **Tier 4 (System Shell):** PowerShell and Windows API commands for volume, explorer search, and system locks.

---

## 2. Directory Structure

```
d:\jarvis\
├── venv\                        # Python 3.13 isolated virtual environment
├── config\
│   ├── config.json              # Local persistent settings (hotkeys, AI keys, voice)
│   └── settings.py              # Configuration manager & Pydantic models
├── core\
│   ├── voice_listener.py        # Audio capture, energy metering & speech recognition
│   ├── hotkey_manager.py        # Global keyboard shortcuts (Ctrl+Alt+Space, Escape)
│   ├── tts_engine.py            # SAPI5 offline voice + ElevenLabs integration
│   ├── brain.py                 # Multi-step action planner (Local rules + LLM)
│   └── safety.py                # Activity logging & emergency stop handler
├── automation\
│   ├── app_launcher.py          # Registry scanner & launcher (CAD, browsers, tools)
│   ├── window_manager.py        # Focus, snap, minimize, restore, and close windows
│   ├── uia_controller.py        # Windows UI Automation button & menu clicker
│   ├── input_controller.py      # Mouse clicks, scroll, and clipboard-based typing
│   ├── system_controller.py     # Volume, screenshot, explorer search, lock
│   └── orchestrator.py          # Multi-step task execution engine with fallback
├── gui\
│   ├── main_window.py           # Modern PySide6 cyberpunk HUD window
│   ├── hud_visualizer.py        # Animated rotating Arc-Reactor audio visualizer
│   ├── system_tray.py           # Windows System Tray icon & context menu
│   └── settings_dialog.py       # GUI configuration dialog
├── assets\
│   ├── icon_active.png          # Glowing cyan system tray & window icon
│   └── icon_inactive.png        # Dimmed red/gray standby icon
├── main.py                      # Application entry point
├── run.bat                      # One-click background launcher
├── setup.bat                    # One-click dependency installer
├── build_exe.bat                # Standalone .exe compiler (PyInstaller)
├── requirements.txt             # Frozen dependency list
└── jarvis.log                   # Real-time execution log
```

---

## 3. Quick Start (1-Click)

### Option A: Launching Directly
Simply double-click:
```bat
run.bat
```
*If this is the first time running, `run.bat` automatically verifies the virtual environment and starts the desktop interface.*

### Option B: Manual Command Line
```powershell
cd d:\jarvis
venv\Scripts\python.exe main.py
```

---

## 4. Key Controls & Shortcuts

| Shortcut / Trigger | Action |
| :--- | :--- |
| **`Ctrl + Alt + Space`** | **Toggle Active Listening (ON / OFF)** |
| **`Escape` (ESC)** | **🛑 EMERGENCY STOP** — Immediately terminates any active automation sequence |
| **"Hey Assistant"** or **"Jarvis"** | Configurable voice wake words |
| **Double-Click System Tray Icon** | Show / Hide HUD Window |
| **Right-Click System Tray Icon** | Quick context menu (Toggle, Settings, Exit) |

---

## 5. Built-in Voice Commands (Examples)

### Application Control
- *"Open SolidWorks"*
- *"Open AutoCAD and create a new drawing"*
- *"Open Chrome and search for mechanical design jobs"*
- *"Open File Explorer and find my project folder"*
- *"Switch to Chrome"* / *"Switch to SolidWorks"*
- *"Close this window"*

### Typing & Text Editing
- *"Type this in Notepad: Hello world from JARVIS voice control"*
- *"Scroll down"* / *"Scroll up"*

### System Functions
- *"Increase volume"* / *"Decrease volume"* / *"Mute"*
- *"Take a screenshot"* (automatically saved to Desktop)
- *"Lock PC"* / *"Lock workstation"*

---

## 6. Configuring AI Brain & Voices

Click the **⚙ Settings** button in the HUD or right-click the system tray icon to configure:
1. **Google Gemini API Key**: Enables dynamic, open-ended reasoning for multi-step instructions not covered by local rules.
2. **Offline SAPI5 Voice**: Choose your installed Windows system voice and adjust speaking speed (WPM).
3. **ElevenLabs API Key (Optional)**: Switch from Windows SAPI5 to movie-grade British voice.
4. **Start with Windows**: Enable automatic startup in background when your PC boots.

---

## 7. Packaging as a Standalone Executable (.exe)

To bundle JARVIS into a standalone Windows application without needing Python installed on other machines:
```bat
build_exe.bat
```
The compiled output will be generated in `dist\JARVIS\JARVIS.exe`.

---

## 8. Troubleshooting

1. **Microphone not detected:**
   - Go to **Windows Settings > Privacy & Security > Microphone** and ensure *"Allow desktop apps to access your microphone"* is turned **ON**.
2. **Elevated Windows / Administrator Apps:**
   - Standard Windows security prevents non-admin apps from sending keystrokes or clicks to elevated windows (e.g. Task Manager or software launched as Administrator). To control elevated windows, right-click `run.bat` and select **"Run as Administrator"**.
3. **Emergency Stop:**
   - If an automated task begins typing or clicking unexpectedly, hit **`Escape`** immediately.
