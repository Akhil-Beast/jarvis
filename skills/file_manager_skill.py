"""
skills/file_manager_skill.py — File and folder management skill.

Handles:
  "read the file X"
  "create a file named X with content Y"
  "list files in X"
  "open file X"
  "delete file X"  (requires confirmation)
"""
import os
import re
from pathlib import Path
from skills.base_skill import BaseSkill
from core.safety import logger


class FileManagerSkill(BaseSkill):

    _PATTERNS = [
        r"^read\s+(?:the\s+)?file\s+(.+)",
        r"^list\s+(?:files|folder)\s+(?:in\s+)?(.+)",
        r"^open\s+file\s+(.+)",
        r"^delete\s+file\s+(.+)",
        r"^(?:create|make|write)\s+(?:a\s+)?file\s+(?:named|called\s+)?(.+?)(?:\s+with\s+content\s+(.+))?$",
    ]

    @property
    def name(self) -> str:
        return "FileManager"

    @property
    def description(self) -> str:
        return "Read, list, create, open, and delete files and folders."

    def can_handle(self, command: str) -> bool:
        c = command.lower().strip()
        return any(re.search(p, c) for p in self._PATTERNS)

    def execute(self, command: str, context: dict | None = None) -> list[dict]:
        c = command.lower().strip()

        # --- READ FILE ---
        m = re.search(r"^read\s+(?:the\s+)?file\s+(.+)", c)
        if m:
            path_str = m.group(1).strip().strip("'\"")
            path = Path(path_str)
            if not path.is_absolute():
                path = Path(os.environ.get("USERPROFILE", "C:/Users/User")) / "Desktop" / path
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                preview = content[:500].replace("\n", " ")
                return [{"action": "speak", "text": f"File contents: {preview}"}]
            except Exception as e:
                return [{"action": "speak", "text": f"Could not read file: {e}"}]

        # --- LIST FILES ---
        m = re.search(r"^list\s+(?:files|folder)\s+(?:in\s+)?(.+)", c)
        if m:
            dir_str = m.group(1).strip().strip("'\"")
            path = Path(dir_str)
            if not path.is_absolute():
                path = Path(os.environ.get("USERPROFILE", "C:/Users/User")) / dir_str
            try:
                items = [p.name for p in path.iterdir()]
                result = ", ".join(items[:10])
                return [{"action": "speak", "text": f"Files in {dir_str}: {result}"}]
            except Exception as e:
                return [{"action": "speak", "text": f"Could not list directory: {e}"}]

        # --- OPEN FILE ---
        m = re.search(r"^open\s+file\s+(.+)", c)
        if m:
            fname = m.group(1).strip().strip("'\"")
            return [
                {"action": "open_app", "target": fname},
                {"action": "speak", "text": f"Opening {fname}."},
            ]

        # --- DELETE FILE (requires confirmation) ---
        m = re.search(r"^delete\s+file\s+(.+)", c)
        if m:
            fname = m.group(1).strip().strip("'\"")
            return [
                {"action": "shell",
                 "command": f'powershell -Command Remove-Item -Path "{fname}" -Force'},
                {"action": "speak", "text": f"Deleted {fname}."},
            ]

        # --- CREATE FILE ---
        m = re.search(r"^(?:create|make|write)\s+(?:a\s+)?file\s+(?:named|called\s+)?(.+?)(?:\s+with\s+content\s+(.+))?$", c)
        if m:
            fname = m.group(1).strip().strip("'\"")
            if not fname.endswith(".txt"):
                fname += ".txt"
            desktop = Path(os.environ.get("USERPROFILE", "C:/Users/User")) / "Desktop"
            full_path = str(desktop / fname)
            content = m.group(2) or ""
            steps: list[dict] = [
                {"action": "shell",
                 "command": f'powershell -Command New-Item -ItemType File -Path "{full_path}" -Force'},
            ]
            if content:
                safe_content = content.replace("'", "`'")
                steps.append({
                    "action": "shell",
                    "command": f"powershell -Command Set-Content -Path '{full_path}' -Value '{safe_content}'"
                })
            steps += [
                {"action": "open_app", "target": full_path},
                {"action": "speak", "text": f"Created {fname} on your desktop."},
            ]
            return steps

        return [{"action": "speak", "text": "File operation not understood, sir."}]
