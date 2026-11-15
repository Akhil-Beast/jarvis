"""
automation/screen_vision.py — Multimodal Desktop Screen Vision & APK Interaction Engine

Capabilities:
1. High-speed Desktop Screen Capture (PySide6 / PIL ImageGrab fallback)
2. Gemini Multimodal Screen Understanding (identifies APKs, text, windows, UI elements)
3. Visual Element Localization (finds pixel coordinates of targets on screen)
4. UI Automation Control Detection (instant accessibility-tree locator)
5. APK Management & Interaction (discovery, aapt metadata inspection, ADB installation, folder opening)
"""
import io
import json
import os
import re
import subprocess
import time
from pathlib import Path
from PIL import Image

from config.settings import config
from core.safety import logger
from automation.input_controller import input_controller
from automation.window_manager import window_manager
from automation.uia_controller import uia_controller

# Known aapt search paths
AAPT_CANDIDATES = [
    Path(r"C:\Users\akhil\AppData\Local\Android\Sdk\build-tools\35.0.0\aapt.exe"),
    Path(r"C:\Users\akhil\AppData\Local\Android\Sdk\build-tools\36.0.0\aapt.exe"),
]

ADB_PATH = Path(r"C:\Users\akhil\AppData\Local\Android\Sdk\platform-tools\adb.exe")


class ScreenVisionEngine:
    """Provides visual perception of the PC screen and interactive APK capabilities."""

    def __init__(self):
        self._aapt_exe = self._find_aapt()

    def _find_aapt(self) -> Path | None:
        for p in AAPT_CANDIDATES:
            if p.exists():
                return p
        return None

    # ------------------------------------------------------------------ #
    # 1. Screen Capture                                                   #
    # ------------------------------------------------------------------ #
    def capture_screen(self, max_width: int = 1280) -> Image.Image | None:
        """Captures full screen cleanly. Scaled down to max_width for fast Gemini upload."""
        img = None

        # Strategy A: PySide6 QGuiApplication grabWindow (fastest & most reliable on Windows)
        try:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
            if screen:
                pixmap = screen.grabWindow(0)
                if not pixmap.isNull():
                    from PySide6.QtCore import QBuffer, QIODevice
                    buffer = QBuffer()
                    buffer.open(QIODevice.ReadWrite)
                    pixmap.save(buffer, "PNG")
                    img = Image.open(io.BytesIO(buffer.data()))
                    logger.info(f"[ScreenVision] Captured via QGuiApplication: {img.size}")
        except Exception as e:
            logger.debug(f"[ScreenVision] Qt capture fallback: {e}")

        # Strategy B: PIL ImageGrab
        if img is None:
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab(all_screens=True)
                logger.info(f"[ScreenVision] Captured via ImageGrab: {img.size}")
            except Exception as e:
                logger.debug(f"[ScreenVision] ImageGrab fallback: {e}")

        if img is None:
            logger.error("[ScreenVision] All screen capture strategies failed.")
            return None

        # Scale down for ultra-fast Gemini network transmission (under 1 second)
        if max_width and img.width > max_width:
            ratio = max_width / float(img.width)
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        return img

    def get_screen_resolution(self) -> tuple[int, int]:
        """Returns native screen width and height in pixels."""
        try:
            import win32api, win32con
            w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            return w, h
        except Exception:
            return 1920, 1080

    # ------------------------------------------------------------------ #
    # 2. Gemini Multimodal Screen Inspection                             #
    # ------------------------------------------------------------------ #
    def inspect_screen(self, user_prompt: str = "") -> str:
        """Takes a screenshot and asks Gemini Vision to describe or find items on it."""
        img = self.capture_screen()
        if not img:
            return "Could not capture the screen at this moment, sir."

        if not config.gemini_api_key:
            return "Gemini API key is not configured for vision analysis, sir."

        prompt = user_prompt.strip() or (
            "Describe what is currently visible on this computer screen. "
            "Highlight any open applications, APK files, download icons, and active windows. "
            "Be concise, conversational, and direct."
        )

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=config.gemini_api_key)
            resp = client.models.generate_content(
                model=config.gemini_model,
                contents=[img, prompt],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=300
                )
            )
            result = resp.text.strip()
            logger.info(f"[ScreenVision] Vision description: {result[:120]}...")
            return result
        except Exception as e:
            logger.error(f"[ScreenVision] Vision inspection error: {e}")
            return f"I had trouble analyzing the screen image: {e}"

    # ------------------------------------------------------------------ #
    # 3. Locate & Interact with Targets (UIA + Vision Coordinate Map)     #
    # ------------------------------------------------------------------ #
    def locate_and_interact(self, target_name: str, click_type: str = "single") -> tuple[bool, str]:
        """
        Locates an element, file, or icon matching target_name on the screen and clicks it.
        Tier 1: Fast UI Automation tree lookup (10ms)
        Tier 2: Gemini Multimodal coordinate prediction (1-2s)
        """
        target = target_name.strip()
        logger.info(f"[ScreenVision] Locating '{target}' on screen for action '{click_type}'...")

        # --- Tier 1: Windows UI Automation (Desktop, Taskbar, Explorer) ---
        uia_clicked = self._try_uia_click(target, click_type)
        if uia_clicked:
            return True, f"Interacted with '{target}' via UI Automation."

        # --- Tier 2: Gemini Vision Coordinate Localization ---
        coords = self._locate_via_gemini_vision(target)
        if coords:
            x, y = coords
            logger.info(f"[ScreenVision] Gemini Vision located '{target}' at screen pixel ({x}, {y})")
            if click_type == "double":
                input_controller.click(x=x, y=y, clicks=2)
            elif click_type == "right":
                input_controller.click(x=x, y=y, clicks=1, button="right")
            else:
                input_controller.click(x=x, y=y, clicks=1, button="left")
            return True, f"Clicked '{target}' on screen at coordinates ({x}, {y})."

        return False, f"Could not see or locate '{target}' on the current screen."

    def _try_uia_click(self, target: str, click_type: str) -> bool:
        """Searches visible UI automation elements on the entire screen."""
        try:
            import uiautomation as auto
            root = auto.GetRootControl()

            # Search Desktop & Explorer list items
            item = root.Control(searchDepth=6, SubName=target)
            if item.Exists(maxSearchSeconds=0.8):
                rect = item.BoundingRectangle
                if rect and not item.IsOffscreen:
                    cx = (rect.left + rect.right) // 2
                    cy = (rect.top + rect.bottom) // 2
                    logger.info(f"[ScreenVision/UIA] Found '{item.Name}' at ({cx}, {cy})")
                    if click_type == "double":
                        input_controller.click(x=cx, y=cy, clicks=2)
                    elif click_type == "right":
                        input_controller.click(x=cx, y=cy, clicks=1, button="right")
                    else:
                        input_controller.click(x=cx, y=cy, clicks=1)
                    return True
        except Exception as e:
            logger.debug(f"[ScreenVision/UIA] Search error: {e}")
        return False

    def _locate_via_gemini_vision(self, target: str) -> tuple[int, int] | None:
        """Prompts Gemini Vision to return normalized coordinates [x_pct, y_pct] for target."""
        img = self.capture_screen()
        if not img or not config.gemini_api_key:
            return None

        prompt = f"""You are a computer vision assistant. Look at this screen and find the element or text: '{target}'.
Return ONLY a JSON object:
{{"found": true, "x_percent": 0.45, "y_percent": 0.32}}
Where x_percent and y_percent are normalized coordinates between 0.0 (left/top) and 1.0 (right/bottom) indicating the CENTER of the element.
If '{target}' is not visible on the screen, return {{"found": false}}.
Zero markdown, zero extra text."""

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=config.gemini_api_key)
            resp = client.models.generate_content(
                model=config.gemini_model,
                contents=[img, prompt],
                config=types.GenerateContentConfig(temperature=0.0)
            )
            text = resp.text.strip()
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            data = json.loads(text)

            if data.get("found") and "x_percent" in data and "y_percent" in data:
                screen_w, screen_h = self.get_screen_resolution()
                x_px = int(data["x_percent"] * screen_w)
                y_px = int(data["y_percent"] * screen_h)
                return x_px, y_px

        except Exception as e:
            logger.warning(f"[ScreenVision] Vision locate failed: {e}")

        return None

    # ------------------------------------------------------------------ #
    # 4. APK Management, Discovery & ADB Interaction                     #
    # ------------------------------------------------------------------ #
    def find_all_apks(self) -> list[dict]:
        """Finds APK files across Desktop, Downloads, and Phone storage quickly without hanging."""
        results = []
        seen_paths = set()

        def _add_if_apk(file_path: Path):
            if str(file_path) not in seen_paths and file_path.is_file() and file_path.name.lower().endswith(".apk"):
                seen_paths.add(str(file_path))
                info = self.inspect_apk(file_path)
                results.append(info)

        # 1. Direct check for known device APKs
        known_apks = [
            Path(r"C:\Users\akhil\CrossDevice\realme P2 Pro 5G (2)\storage\BankAnalyzer.apk"),
            Path(r"C:\Users\akhil\CrossDevice\realme P2 Pro 5G (2)\storage\Download\BankAnalyzer.apk"),
            Path(r"C:\Users\akhil\CrossDevice\I2403\storage\BankAnalyzer.apk"),
        ]
        for k in known_apks:
            try:
                if k.exists():
                    _add_if_apk(k)
            except Exception:
                pass

        # 2. Fast non-recursive check of user local directories
        local_dirs = [
            Path(r"C:\Users\akhil\OneDrive\Desktop"),
            Path(r"C:\Users\akhil\Downloads"),
            Path(os.environ.get("USERPROFILE", "C:")) / "Desktop",
            Path(os.environ.get("USERPROFILE", "C:")) / "Downloads",
            Path(r"D:\jarvis"),
        ]
        for d in local_dirs:
            if not d.exists():
                continue
            try:
                for entry in os.listdir(d):
                    if entry.lower().endswith(".apk"):
                        _add_if_apk(d / entry)
            except Exception:
                continue

        return results

    def inspect_apk(self, apk_path: Path | str) -> dict:
        """Extracts APK package name, app label, and version via aapt."""
        p = Path(apk_path)
        info = {
            "path": str(p),
            "filename": p.name,
            "app_name": p.stem,
            "package_name": "",
            "version": "",
            "size_mb": round(p.stat().st_size / (1024 * 1024), 2) if p.exists() else 0.0
        }

        if self._aapt_exe and p.exists():
            try:
                out = subprocess.check_output(
                    [str(self._aapt_exe), "dump", "badging", str(p)],
                    stderr=subprocess.DEVNULL,
                    text=True,
                    encoding="utf-8",
                    errors="replace"
                )
                # Parse package name
                m_pkg = re.search(r"package:\s+name='([^']+)'", out)
                if m_pkg:
                    info["package_name"] = m_pkg.group(1)

                # Parse version
                m_ver = re.search(r"versionName='([^']+)'", out)
                if m_ver:
                    info["version"] = m_ver.group(1)

                # Parse application label
                m_label = re.search(r"application-label(?:-en)?:'([^']+)'", out)
                if m_label:
                    info["app_name"] = m_label.group(1)

            except Exception as e:
                logger.debug(f"[ScreenVision] aapt dump error on {p.name}: {e}")

        return info

    def install_apk(self, apk_target: str = "") -> tuple[bool, str]:
        """Installs an APK to a connected ADB device or emulator."""
        # Find the target APK
        target_path = None
        if apk_target and Path(apk_target).exists():
            target_path = Path(apk_target)
        else:
            all_apks = self.find_all_apks()
            if apk_target:
                for apk in all_apks:
                    if apk_target.lower() in apk["filename"].lower() or apk_target.lower() in apk["app_name"].lower():
                        target_path = Path(apk["path"])
                        break
            elif all_apks:
                target_path = Path(all_apks[0]["path"])

        if not target_path or not target_path.exists():
            return False, f"Could not find any APK matching '{apk_target}' to install."

        # Check if ADB device is connected
        try:
            devices_out = subprocess.check_output([str(ADB_PATH), "devices"], text=True)
            lines = [l.strip() for l in devices_out.splitlines() if l.strip() and not l.startswith("List of")]
            if not lines:
                # No ADB device, open the containing folder in File Explorer so the user can interact
                subprocess.Popen(f'explorer.exe /select,"{target_path}"', shell=True)
                return True, f"No ADB device connected. Opened and selected '{target_path.name}' in File Explorer."

            # ADB device is connected — perform install
            logger.info(f"[ScreenVision] Installing '{target_path.name}' via ADB...")
            proc = subprocess.run([str(ADB_PATH), "install", "-r", str(target_path)], capture_output=True, text=True, timeout=30)
            if "Success" in proc.stdout:
                return True, f"Successfully installed {target_path.name} to connected device."
            else:
                return False, f"ADB install failed: {proc.stderr or proc.stdout}"

        except Exception as e:
            # Fallback: open folder in explorer
            subprocess.Popen(f'explorer.exe /select,"{target_path}"', shell=True)
            return True, f"Opened '{target_path.name}' in File Explorer: {e}"

    def show_apk_in_explorer(self, apk_target: str = "") -> tuple[bool, str]:
        """Opens File Explorer and highlights the target APK."""
        all_apks = self.find_all_apks()
        target_apk = None
        if apk_target:
            for a in all_apks:
                if apk_target.lower() in a["filename"].lower() or apk_target.lower() in a["app_name"].lower():
                    target_apk = a
                    break
        elif all_apks:
            target_apk = all_apks[0]

        if not target_apk:
            return False, "No APK files found on this machine, sir."

        path = target_apk["path"]
        subprocess.Popen(f'explorer.exe /select,"{path}"', shell=True)
        return True, f"Showing {target_apk['app_name']} ({target_apk['filename']}) in File Explorer."


screen_vision = ScreenVisionEngine()
