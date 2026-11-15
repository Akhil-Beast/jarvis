import os
import subprocess
import time
import winreg
from pathlib import Path
import psutil
from core.safety import logger
from automation.window_manager import window_manager


class AppLauncher:
    """Discovers, launches, and switches to Windows desktop and Store applications."""

    # Built-in fast-path registry for popular professional software
    KNOWN_APPS = {
        "chrome": ["chrome.exe", "google chrome"],
        "google chrome": ["chrome.exe"],
        "edge": ["msedge.exe", "microsoft edge"],
        "firefox": ["firefox.exe"],
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "calc": ["calc.exe"],
        "file explorer": ["explorer.exe"],
        "explorer": ["explorer.exe"],
        "files": ["explorer.exe"],
        "excel": ["excel.exe", "microsoft excel"],
        "word": ["winword.exe", "microsoft word"],
        "powerpoint": ["powerpnt.exe"],
        "solidworks": ["SLDWORKS.exe", "solidworks"],
        "autocad": ["acad.exe", "autocad"],
        "inventor": ["inventor.exe"],
        "fusion": ["fusion360.exe", "Autodesk Fusion 360"],
        "fusion 360": ["fusion360.exe"],
        "catia": ["CNEXT.exe"],
        "vscode": ["code.exe", "visual studio code"],
        "visual studio code": ["code.exe"],
        "terminal": ["wt.exe", "windows terminal"],
        "powershell": ["powershell.exe"],
        "cmd": ["cmd.exe", "command prompt"],
        "spotify": ["spotify.exe"],
        "vlc": ["vlc.exe"],
        "paint": ["mspaint.exe"]
    }

    def __init__(self):
        self._installed_cache = {}
        self._refresh_installed_apps()

    def _refresh_installed_apps(self):
        """Scans Windows Registry for registered application paths."""
        paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
        ]
        for root_key, subkey in paths:
            try:
                with winreg.OpenKey(root_key, subkey) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            app_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, app_name) as app_key:
                                exe_path, _ = winreg.QueryValueEx(app_key, "")
                                self._installed_cache[app_name.lower()] = exe_path
                                if app_name.lower().endswith(".exe"):
                                    self._installed_cache[app_name[:-4].lower()] = exe_path
                        except Exception:
                            continue
            except Exception:
                continue

    def launch(self, name_or_path: str) -> tuple[bool, str]:
        """Launches an application or brings it to focus if already running."""
        name_clean = name_or_path.strip().lower()
        logger.info(f"[AppLauncher] Launching/focusing '{name_clean}'")

        # 1. First, check if a window for this application is already open and visible.
        #    If so, bring it to the foreground immediately (sub-100ms response).
        target_exes = self.KNOWN_APPS.get(name_clean, [name_clean])
        keywords_to_check = [name_clean] + [e.replace(".exe", "") for e in target_exes]

        for kw in keywords_to_check:
            if window_manager.focus_window(kw):
                logger.info(f"[AppLauncher] Focused existing window matching '{kw}'.")
                return True, f"Focused {name_clean} window."

        # 2. Window is not open — launch the application.
        # Check known target executables
        candidates = list(target_exes)
        if not any(e.endswith(".exe") for e in candidates):
            candidates.append(f"{name_clean}.exe")

        # 3. Check Windows App Paths Registry Cache
        for target in candidates:
            target_key = target.lower()
            if target_key in self._installed_cache:
                exe = self._installed_cache[target_key]
                try:
                    subprocess.Popen(f'"{exe}"', shell=True)
                    logger.info(f"[AppLauncher] Launched {name_clean} from registry: {exe}")
                    return True, f"Started {name_clean} from {exe}"
                except Exception as e:
                    logger.warning(f"Failed to start cached path {exe}: {e}")

        # 4. Try Direct os.startfile (handles system utilities, shell associations, URLs)
        for target in [name_clean] + candidates:
            try:
                os.startfile(target)
                logger.info(f"[AppLauncher] Launched via os.startfile: {target}")
                return True, f"Started {target}"
            except Exception:
                pass

        # 5. Try Windows command prompt start
        for target in candidates:
            try:
                proc = subprocess.Popen(f'cmd /c start "" "{target}"', shell=True)
                proc.wait(timeout=2)
                logger.info(f"[AppLauncher] Launched via cmd start: {target}")
                return True, f"Started {target}"
            except Exception:
                pass

        # 6. Try PowerShell Start-Process as final launch fallback
        try:
            proc = subprocess.Popen(["powershell", "-Command", f"Start-Process '{name_clean}'"], shell=False)
            proc.wait(timeout=3)
            logger.info(f"[AppLauncher] Launched via PowerShell Start-Process: {name_clean}")
            return True, f"Launched {name_clean} via PowerShell"
        except Exception as e:
            logger.error(f"[AppLauncher] Could not launch '{name_clean}': {e}")
            return False, f"Could not find or launch application '{name_or_path}'."


app_launcher = AppLauncher()
