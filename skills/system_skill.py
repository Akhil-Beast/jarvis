"""
skills/system_skill.py — System-level commands skill.

Handles extra system commands not covered by brain.py local rules:
  "what is my IP address"
  "show running processes"
  "open task manager"
  "empty recycle bin"
  "open control panel"
  "show battery status"
"""
import re
import subprocess
from skills.base_skill import BaseSkill
from core.safety import logger


class SystemSkill(BaseSkill):

    _PATTERNS = [
        r"(?:what(?:'s| is) my|show|get|check)\s+ip\s+address",
        r"(?:show|list|what are)\s+(?:running\s+)?processes",
        r"empty\s+recycle\s+bin",
        r"open\s+control\s+panel",
        r"(?:battery|power)\s+status",
        r"disk\s+(?:usage|space|info)",
        r"system\s+info(?:rmation)?",
    ]

    @property
    def name(self) -> str:
        return "System"

    @property
    def description(self) -> str:
        return "System-level queries: IP, processes, battery, disk, control panel."

    def can_handle(self, command: str) -> bool:
        c = command.lower().strip()
        return any(re.search(p, c) for p in self._PATTERNS)

    def execute(self, command: str, context: dict | None = None) -> list[dict]:
        c = command.lower().strip()

        if re.search(r"ip\s+address", c):
            try:
                result = subprocess.check_output(
                    ["powershell", "-Command",
                     "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike '*Loopback*' } | Select-Object -First 1).IPAddress"],
                    text=True, timeout=5
                ).strip()
                return [{"action": "speak", "text": f"Your IP address is {result}."}]
            except Exception:
                return [{"action": "speak", "text": "Could not retrieve IP address, sir."}]

        if re.search(r"empty\s+recycle\s+bin", c):
            return [
                {"action": "shell", "command": "powershell -Command Clear-RecycleBin -Force"},
                {"action": "speak", "text": "Recycle bin emptied, sir."},
            ]

        if re.search(r"control\s+panel", c):
            return [
                {"action": "shell", "command": "cmd /c start control"},
                {"action": "speak", "text": "Opening Control Panel."},
            ]

        if re.search(r"(?:battery|power)\s+status", c):
            try:
                result = subprocess.check_output(
                    ["powershell", "-Command",
                     "(Get-WmiObject Win32_Battery | Select-Object -First 1).EstimatedChargeRemaining"],
                    text=True, timeout=5
                ).strip()
                return [{"action": "speak", "text": f"Battery charge is {result} percent, sir."}]
            except Exception:
                return [{"action": "speak", "text": "Could not retrieve battery status."}]

        if re.search(r"disk\s+(?:usage|space|info)", c):
            try:
                result = subprocess.check_output(
                    ["powershell", "-Command",
                     "Get-PSDrive C | Select-Object -ExpandProperty Used,Free | ForEach-Object { [math]::Round($_ / 1GB, 1) }"],
                    text=True, timeout=5
                ).strip()
                return [{"action": "speak", "text": f"Disk info: {result} gigabytes."}]
            except Exception:
                return [{"action": "speak", "text": "Could not retrieve disk information."}]

        if re.search(r"system\s+info", c):
            return [
                {"action": "shell", "command": "cmd /c start msinfo32"},
                {"action": "speak", "text": "Opening System Information."},
            ]

        return [{"action": "speak", "text": "System command not recognised, sir."}]
