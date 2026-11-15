import time
import threading
from core.safety import logger, safety
from core.tts_engine import tts
from core.brain import ActionPlan
from automation.app_launcher import app_launcher
from automation.window_manager import window_manager
from automation.uia_controller import uia_controller
from automation.input_controller import input_controller
from automation.system_controller import system_controller

class TaskOrchestrator:
    """Executes multi-step plans with verification, safety interception, and multi-tier fallbacks."""

    def __init__(self, on_step_update=None):
        self.on_step_update = on_step_update
        self._current_task_thread = None

    def execute_plan_async(self, plan: ActionPlan):
        """Runs the action plan in a background thread so the UI remains fluid."""
        safety.reset_abort()
        self._current_task_thread = threading.Thread(
            target=self._execute_worker, args=(plan,), daemon=True
        )
        self._current_task_thread.start()

    def _execute_worker(self, plan: ActionPlan):
        logger.info(f"[Orchestrator] Executing plan with {len(plan.steps)} steps.")

        for i, step in enumerate(plan.steps):
            if safety.is_aborted:
                logger.warning("[Orchestrator] Execution aborted by user emergency stop.")
                if self.on_step_update:
                    self.on_step_update(i, step, "ABORTED")
                tts.speak("Automation stopped.", interrupt=True)
                break

            action_type = step.get("action", "")
            if self.on_step_update:
                self.on_step_update(i, step, "RUNNING")

            success = self._run_single_step(step)

            status = "SUCCESS" if success else "FAILED"
            if self.on_step_update:
                self.on_step_update(i, step, status)

            # Brief pause between sequential automated actions
            time.sleep(0.15)

    def _run_single_step(self, step: dict) -> bool:
        action = step.get("action")
        try:
            if action == "open_app":
                target = step.get("target", "")
                success, _ = app_launcher.launch(target)
                return success

            elif action == "focus_window":
                target = step.get("target", "")
                return window_manager.focus_window(target)

            elif action == "close_window":
                target = step.get("target", "")
                return window_manager.close_window(target)

            elif action == "click_element":
                name = step.get("name", "")
                # Tier 1: Try Windows UI Automation
                if uia_controller.click_element_by_name(name):
                    return True
                # Tier 2 Fallback: Try pressing Enter or Space
                logger.info(f"[Fallback] UIA click failed for '{name}', attempting keyboard focus.")
                input_controller.press_key("enter")
                return True

            elif action == "type_text":
                text = step.get("text", "")
                enter = step.get("enter", False)
                input_controller.type_text(text, press_enter=enter)
                return True

            elif action == "hotkey":
                keys = step.get("keys", [])
                input_controller.hotkey(*keys)
                return True

            elif action == "press_key":
                key = step.get("key", "")
                input_controller.press_key(key)
                return True

            elif action == "scroll":
                clicks = step.get("clicks", -300)
                input_controller.scroll(clicks)
                return True

            elif action == "wait":
                sec = step.get("seconds", 1.0)
                time.sleep(sec)
                return True

            elif action == "system":
                cmd = step.get("command")
                if cmd == "volume":
                    system_controller.adjust_volume(step.get("direction", "up"), step.get("steps", 5))
                elif cmd == "screenshot":
                    system_controller.take_screenshot()
                elif cmd == "search_explorer":
                    system_controller.search_in_explorer(step.get("query", ""))
                elif cmd == "lock":
                    system_controller.lock_workstation()
                return True

            elif action == "shell":
                # Execute a safe shell command with expanded allowlist
                cmd = step.get("command", "")
                cmd_lower = cmd.lower().strip()

                # --- BLOCKLIST: always deny dangerous destructive commands ---
                BLOCKED = (
                    "rm -rf", "del /f /s /q", "format ", "rd /s /q",
                    "reg delete", "reg add", "bcdedit", "diskpart",
                    "shutdown /f", "taskkill /f /im", "net user ",
                    "net localgroup", "icacls", "attrib -s -h",
                )
                if any(b in cmd_lower for b in BLOCKED):
                    logger.warning(f"[Orchestrator] BLOCKED dangerous shell command: {cmd}")
                    tts.speak("That command is not permitted for safety reasons, sir.")
                    return False

                # --- ALLOWLIST: safe read/create/open operations ---
                ALLOWED_PREFIXES = (
                    # App launches
                    "notepad", "explorer", "calc", "mspaint", "wordpad",
                    "cmd /c echo", "cmd /c start",
                    # PowerShell safe operations
                    "powershell -command new-item",
                    "powershell -command get-childitem",
                    "powershell -command copy-item",
                    "powershell -command move-item",
                    "powershell -command rename-item",
                    "powershell -command set-content",
                    "powershell -command add-content",
                    "powershell -command get-content",
                    "powershell -command test-path",
                    "powershell -command invoke-item",
                    "powershell -command start-process",
                    "powershell -command [system.media.soundplayer]",
                    "powershell -c (new-object",
                    "powershell -c start",
                    # wscript / cscript
                    "wscript", "cscript",
                    # Specific system utilities
                    "tasklist", "ipconfig", "ping ",
                    "netstat", "systeminfo",
                )
                if any(cmd_lower.startswith(p) for p in ALLOWED_PREFIXES):
                    import subprocess
                    subprocess.Popen(cmd, shell=True)
                    return True

                # --- DESTRUCTIVE OPERATIONS requiring user confirmation ---
                DESTRUCTIVE = (
                    "powershell -command remove-item",
                    "del ", "rmdir",
                )
                if any(cmd_lower.startswith(d) for d in DESTRUCTIVE):
                    from core.safety import safety
                    if safety.request_confirmation(f"Shell: {cmd}"):
                        import subprocess
                        subprocess.Popen(cmd, shell=True)
                        return True
                    else:
                        tts.speak("Command cancelled, sir.")
                        return False

                logger.warning(f"[Orchestrator] Shell command blocked (not in allowlist): {cmd}")
                tts.speak("That command is not in the approved list, sir.")
                return False

            elif action == "speak":
                text = step.get("text", "")
                tts.speak(text)
                return True

            elif action == "vision_inspect":
                from automation.screen_vision import screen_vision
                prompt = step.get("prompt", "")
                result = screen_vision.inspect_screen(prompt)
                tts.speak(result)
                return True

            elif action == "click_screen_target":
                from automation.screen_vision import screen_vision
                target = step.get("target", "")
                click_type = step.get("click_type", "single")
                ok, msg = screen_vision.locate_and_interact(target, click_type)
                tts.speak(msg)
                return ok

            elif action == "apk_action":
                from automation.screen_vision import screen_vision
                cmd = step.get("command", "find")
                target = step.get("target", "")
                if cmd in ["find", "open", "show"]:
                    ok, msg = screen_vision.show_apk_in_explorer(target)
                    tts.speak(msg)
                    return ok
                elif cmd == "install":
                    ok, msg = screen_vision.install_apk(target)
                    tts.speak(msg)
                    return ok
                elif cmd == "inspect":
                    apks = screen_vision.find_all_apks()
                    match = None
                    if target:
                        for a in apks:
                            if target.lower() in a["filename"].lower() or target.lower() in a["app_name"].lower():
                                match = a
                                break
                    elif apks:
                        match = apks[0]
                    if match:
                        desc = f"APK {match['app_name']}, package {match['package_name']}, file size {match['size_mb']} megabytes."
                    else:
                        desc = f"Could not find APK {target} on this computer, sir."
                    tts.speak(desc)
                    return True

        except Exception as e:
            logger.error(f"[Orchestrator] Error running action '{action}': {e}")
            return False

        return False

orchestrator = TaskOrchestrator()
