import json
import re
import time
from config.settings import config
from core.safety import logger
from automation.window_manager import window_manager
from automation.uia_controller import uia_controller

class ActionPlan:
    """Standardized multi-step action representation."""
    def __init__(self, steps: list[dict], explanation: str = ""):
        self.steps = steps
        self.explanation = explanation

class AIBrain:
    """Translates natural language voice commands into executable multi-step automation plans."""

    def __init__(self):
        pass

    def plan_command(self, user_command: str) -> ActionPlan:
        """Determines steps using fast local rules first, falling back to LLM for complex tasks."""
        cmd = user_command.strip()
        logger.info(f"[Brain] Planning for input: '{cmd}'")

        # 1. Try Fast Local Rules first (instant execution, zero latency)
        local_plan = self._try_local_rules(cmd)
        if local_plan:
            return local_plan

        # 2. Try LLM if configured
        llm_plan = self._try_llm_planning(cmd)
        if llm_plan:
            return llm_plan

        # 3. Fallback generic web search or speech
        return ActionPlan(
            steps=[
                {"action": "speak", "text": f"I heard: {cmd}, but I am not certain how to execute that task."}
            ],
            explanation="Unrecognized command fallback"
        )

    def _try_local_rules(self, cmd: str) -> ActionPlan | None:
        c = cmd.lower()

        # Volume control
        if "volume up" in c or "increase volume" in c or "louder" in c:
            return ActionPlan([
                {"action": "system", "command": "volume", "direction": "up", "steps": 5},
                {"action": "speak", "text": "Increasing volume."}
            ])
        if "volume down" in c or "decrease volume" in c or "quieter" in c:
            return ActionPlan([
                {"action": "system", "command": "volume", "direction": "down", "steps": 5},
                {"action": "speak", "text": "Lowering volume."}
            ])
        if "mute" in c or "unmute" in c:
            return ActionPlan([
                {"action": "system", "command": "volume", "direction": "mute", "steps": 1},
                {"action": "speak", "text": "Volume muted."}
            ])

        # Screenshot
        if "screenshot" in c or "capture screen" in c:
            return ActionPlan([
                {"action": "system", "command": "screenshot"},
                {"action": "speak", "text": "Screenshot captured and saved to your desktop."}
            ])

        # Lock Workstation
        if "lock pc" in c or "lock computer" in c or "lock workstation" in c:
            return ActionPlan([
                {"action": "speak", "text": "Locking workstation."},
                {"action": "system", "command": "lock"}
            ])

        # Scroll
        if "scroll down" in c:
            return ActionPlan([{"action": "scroll", "clicks": -500}])
        if "scroll up" in c:
            return ActionPlan([{"action": "scroll", "clicks": 500}])

        # Multi-step: "Open Chrome and search for X"
        m = re.match(r"(?:open|launch)\s+chrome\s+and\s+search\s+(?:for\s+)?(.+)", c)
        if m:
            query = m.group(1).strip()
            return ActionPlan([
                {"action": "open_app", "target": "chrome"},
                {"action": "wait", "seconds": 1.2},
                {"action": "hotkey", "keys": ["ctrl", "t"]},
                {"action": "type_text", "text": query, "enter": True},
                {"action": "speak", "text": f"Searching for {query} on Chrome."}
            ])

        # Multi-step: "Open File Explorer and find/search X"
        m = re.match(r"(?:open|launch)\s+(?:file\s+)?explorer\s+and\s+(?:find|search\s+for\s+)?(.+)", c)
        if m:
            folder_or_file = m.group(1).strip()
            return ActionPlan([
                {"action": "system", "command": "search_explorer", "query": folder_or_file},
                {"action": "speak", "text": f"Searching File Explorer for {folder_or_file}."}
            ])

        # Multi-step: "Type this in notepad: X" or "Type this paragraph in notepad"
        m = re.match(r"type\s+(?:this\s+)?(?:paragraph\s+)?(?:in|into)\s+notepad:?\s*(.*)", c)
        if m:
            text_to_type = m.group(1).strip() or "Voice note from JARVIS"
            return ActionPlan([
                {"action": "open_app", "target": "notepad"},
                {"action": "wait", "seconds": 1.0},
                {"action": "type_text", "text": text_to_type, "enter": True},
                {"action": "speak", "text": "Pasted text into Notepad."}
            ])

        # Multi-step CAD: "Open AutoCAD and create a new drawing"
        if "autocad" in c and ("new drawing" in c or "new file" in c):
            return ActionPlan([
                {"action": "open_app", "target": "autocad"},
                {"action": "wait", "seconds": 2.5},
                {"action": "hotkey", "keys": ["ctrl", "n"]},
                {"action": "speak", "text": "Opening AutoCAD and creating a new drawing."}
            ])

        # Multi-step CAD: "Open SolidWorks"
        if "solidworks" in c:
            return ActionPlan([
                {"action": "open_app", "target": "solidworks"},
                {"action": "speak", "text": "Launching SolidWorks."}
            ])

        # Switch to app: "switch to X"
        m = re.match(r"switch\s+to\s+(.+)", c)
        if m:
            target = m.group(1).strip()
            return ActionPlan([
                {"action": "focus_window", "target": target},
                {"action": "speak", "text": f"Switching to {target}."}
            ])

        # Open app: "open X" or "launch X"
        m = re.match(r"(?:open|launch)\s+(.+)", c)
        if m:
            target = m.group(1).strip()
            return ActionPlan([
                {"action": "open_app", "target": target},
                {"action": "speak", "text": f"Opening {target}."}
            ])

        # Close window / app: "close X"
        m = re.match(r"close\s+(.+)", c)
        if m:
            target = m.group(1).strip()
            if target in ["window", "this window", "active window"]:
                return ActionPlan([
                    {"action": "close_window", "target": ""},
                    {"action": "speak", "text": "Closing active window."}
                ])
            return ActionPlan([
                {"action": "close_window", "target": target},
                {"action": "speak", "text": f"Closing {target}."}
            ])

        return None

    def _try_llm_planning(self, cmd: str) -> ActionPlan | None:
        """Invokes Gemini or OpenAI to plan arbitrary multi-step desktop tasks."""
        if not config.gemini_api_key and not config.openai_api_key:
            return None

        windows = [w["title"] for w in window_manager.get_open_windows()][:5]
        ui_elements = uia_controller.get_visible_ui_summary(max_elements=15)

        system_prompt = f"""You are the AI brain of JARVIS, a Windows desktop automation assistant.
Convert the user's voice command into a JSON action sequence.

Open Windows: {windows}
Active UI Elements: {json.dumps(ui_elements)}

Allowed Actions:
- open_app: {{"action": "open_app", "target": "app_name"}}
- focus_window: {{"action": "focus_window", "target": "window_title"}}
- close_window: {{"action": "close_window", "target": "window_title_or_empty"}}
- click_element: {{"action": "click_element", "name": "button_or_menu_name"}}
- type_text: {{"action": "type_text", "text": "content", "enter": true/false}}
- hotkey: {{"action": "hotkey", "keys": ["ctrl", "s"]}}
- press_key: {{"action": "press_key", "key": "enter"}}
- wait: {{"action": "wait", "seconds": 1.0}}
- system: {{"action": "system", "command": "volume|screenshot|lock|search_explorer", "direction": "up|down", "query": "..."}}
- speak: {{"action": "speak", "text": "Brief confirmation to user"}}

Respond ONLY with a valid JSON array of action objects. No markdown formatting, no commentary.
"""
        try:
            if config.gemini_api_key:
                from google import genai
                client = genai.Client(api_key=config.gemini_api_key)
                response = client.models.generate_content(
                    model=config.gemini_model,
                    contents=f"{system_prompt}\nUser Command: {cmd}"
                )
                text = response.text.strip()
                # Clean possible markdown block
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\n", "", text)
                    text = re.sub(r"\n```$", "", text)
                steps = json.loads(text)
                return ActionPlan(steps=steps, explanation="Planned via Gemini")
        except Exception as e:
            logger.warning(f"[Brain] LLM planning failed: {e}")

        return None

brain = AIBrain()
