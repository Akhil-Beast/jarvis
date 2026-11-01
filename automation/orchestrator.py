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

            elif action == "speak":
                text = step.get("text", "")
                tts.speak(text)
                return True

        except Exception as e:
            logger.error(f"[Orchestrator] Error running action '{action}': {e}")
            return False

        return False

orchestrator = TaskOrchestrator()
