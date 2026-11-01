import os
import subprocess
import winreg
from pathlib import Path
import psutil
from core.safety import logger

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
                                # also map without .exe
                                if app_name.lower().endswith(".exe"):
                                    self._installed_cache[app_name[:-4].lower()] = exe_path
                        except Exception:
                            continue
            except Exception:
                continue

    def launch(self, name_or_path: str) -> tuple[bool, str]:
        """Launches an application or brings it to focus if already running."""
        name_clean = name_or_path.strip().lower()
        logger.info(f"[AppLauncher] Attempting to launch '{name_clean}'")

        # 1. Check known aliases
        target_exes = self.KNOWN_APPS.get(name_clean, [name_clean])
        if not any(e.endswith(".exe") for e in target_exes):
            target_exes.append(f"{name_clean}.exe")

        # 2. Check if already running in memory
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                pname = proc.info['name'].lower()
                for target in target_exes:
                    if target.lower() in pname or pname in target.lower():
                        logger.info(f"[AppLauncher] '{pname}' is already running (PID {proc.info['pid']}).")
                        return True, f"{pname} is already active."
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # 3. Check App Paths registry cache
        for target in target_exes:
            target_key = target.lower()
            if target_key in self._installed_cache:
                exe = self._installed_cache[target_key]
                try:
                    subprocess.Popen(f'"{exe}"', shell=True)
                    return True, f"Started {target} from {exe}"
                except Exception as e:
                    logger.warning(f"Failed to start cached path {exe}: {e}")

        # 4. Try Direct Shell Start (works for Windows system commands, URLs, and PATH exes)
        try:
            os.startfile(name_or_path)
            return True, f"Started {name_or_path}"
        except Exception:
            pass

        # 5. Try start command via PowerShell
        try:
            proc = subprocess.Popen(["powershell", "-Command", f"Start-Process '{name_clean}'"], shell=False)
            proc.wait(timeout=3)
            return True, f"Launched {name_clean} via PowerShell"
        except Exception as e:
            logger.error(f"[AppLauncher] Could not launch '{name_clean}': {e}")
            return False, f"Could not find or launch application '{name_or_path}'."

app_launcher = AppLauncher()
