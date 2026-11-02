"""
core/brain.py — Autonomous Desktop Action Planning Engine
Translates user voice input into concrete Windows execution steps.

Guarantees:
- NEVER explains how to do a task verbally; ALWAYS executes the action on the PC.
- Strips conversational wrappers ("how to", "tell me how to", "can you", "please").
- Instant local rules for common desktop actions (zero latency).
- Direct Handy-style text injection for dictation into active apps.
- Autonomous Gemini execution planner for complex multi-step instructions.
"""
import json
import os
import re
import subprocess
import time
from pathlib import Path
from config.settings import config
from core.safety import logger
from automation.window_manager import window_manager
from automation.uia_controller import uia_controller
from automation.handy_injector import handy_injector


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
        raw_cmd = user_command.strip()
        cmd = self._normalize_intent(raw_cmd)
        logger.info(f"[Brain] Normalized command: '{raw_cmd}' -> '{cmd}'")

        # 1. Fast local execution rules (instant, zero network latency)
        local_plan = self._try_local_rules(cmd)
        if local_plan:
            logger.info(f"[Brain] Matched local action rule ({local_plan.explanation})")
            return local_plan

        # 2. Autonomous LLM planner (Gemini)
        llm_plan = self._try_llm_planning(cmd)
        if llm_plan and not self._is_passive_tutorial(llm_plan, cmd):
            return llm_plan

        # 3. Smart execution fallback — open/run target directly
        shell_plan = self._smart_shell_fallback(cmd)
        if shell_plan:
            return shell_plan

        # 4. Handy Dictation Fallback: If user is dictating sentences, inject directly into active window
        if len(cmd.split()) >= 3 and not any(w in cmd.lower() for w in ["open", "close", "delete", "shutdown"]):
            return ActionPlan(
                steps=[
                    {"action": "type_text", "text": raw_cmd, "enter": False},
                    {"action": "speak", "text": "Typed into active window."}
                ],
                explanation="Handy direct text injection fallback"
            )

        # 5. Last resort — launch Google search for query
        return ActionPlan(
            steps=[
                {"action": "open_app", "target": "chrome"},
                {"action": "wait", "seconds": 1.2},
                {"action": "hotkey", "keys": ["ctrl", "t"]},
                {"action": "type_text", "text": f"https://www.google.com/search?q={cmd.replace(' ', '+')}", "enter": True},
                {"action": "speak", "text": f"Searching for {cmd}."}
            ],
            explanation="Web search execution"
        )

    # ------------------------------------------------------------------ #
    # Intent Normalizer: Strips passive tutorial wrappers                #
    # ------------------------------------------------------------------ #
    def _normalize_intent(self, text: str) -> str:
        """Converts 'how do I open notepad' or 'tell me how to do X' into 'open notepad' / 'do X'."""
        cleaned = text.strip()

        prefixes = [
            r"^(?:please\s+)?(?:can|could|would)\s+you\s+(?:please\s+)?",
            r"^(?:tell\s+me\s+)?how\s+(?:do\s+i|to|can\s+i)\s+",
            r"^how\s+can\s+we\s+",
            r"^(?:tell\s+me\s+)?how\s+to\s+execute\s+(?:the\s+task\s+)?(?:of\s+)?",
            r"^(?:execute|run|perform)\s+(?:the\s+task\s+)?(?:of\s+)?",
            r"^(?:tell\s+me\s+)?how\s+do\s+you\s+",
            r"^i\s+want\s+(?:you\s+to\s+)?",
            r"^i\s+need\s+(?:you\s+to\s+)?",
            r"^go\s+ahead\s+and\s+",
            r"^just\s+",
            r"^help\s+me\s+(?:to\s+)?",
        ]
        for p in prefixes:
            cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE).strip()

        # Clean trailing question marks
        cleaned = cleaned.rstrip("?").strip()
        return cleaned

    def _is_passive_tutorial(self, plan: ActionPlan, cmd: str) -> bool:
        """Returns True if the plan only talks/explains instead of taking desktop actions."""
        if not plan.steps:
            return True
        non_speak_steps = [s for s in plan.steps if s.get("action") != "speak"]
        # If there are no physical action steps, and the user wanted an action, it's a passive tutorial!
        action_verbs = ["open", "launch", "create", "make", "delete", "search", "click", "type", "press", "close", "lock", "screenshot", "save"]
        if not non_speak_steps and any(v in cmd.lower() for v in action_verbs):
            logger.warning(f"[Brain] Rejected passive tutorial plan for action command '{cmd}'")
            return True
        return False

    # ------------------------------------------------------------------ #
    # Smart Shell Fallback                                                 #
    # ------------------------------------------------------------------ #
    def _smart_shell_fallback(self, cmd: str) -> ActionPlan | None:
        c = cmd.lower().strip()
        m = re.match(r"(?:open|launch|start|run)\s+(.+)", c)
        if m:
            target = m.group(1).strip()
            return ActionPlan(
                steps=[
                    {"action": "open_app", "target": target},
                    {"action": "speak", "text": f"Launching {target}."}
                ],
                explanation=f"Smart shell launch: {target}"
            )
        return None

    # ------------------------------------------------------------------ #
    # Local Action Rules (Instant execution, zero latency)               #
    # ------------------------------------------------------------------ #
    def _try_local_rules(self, cmd: str) -> ActionPlan | None:
        c = cmd.lower().strip()

        # ---- SYSTEM CONTROLS ----
        for kw in ["volume up", "increase volume", "louder", "turn up volume", "raise volume",
                   "increase the volume", "turn up the volume", "volume higher"]:
            if kw in c:
                return ActionPlan([
                    {"action": "system", "command": "volume", "direction": "up", "steps": 5},
                    {"action": "speak", "text": "Volume increased."}
                ], "volume up")

        for kw in ["volume down", "decrease volume", "quieter", "turn down volume", "lower volume",
                   "decrease the volume", "turn down the volume", "volume lower"]:
            if kw in c:
                return ActionPlan([
                    {"action": "system", "command": "volume", "direction": "down", "steps": 5},
                    {"action": "speak", "text": "Volume decreased."}
                ], "volume down")

        if re.search(r"\b(mute|unmute|silence)\b", c):
            return ActionPlan([
                {"action": "system", "command": "volume", "direction": "mute", "steps": 1},
                {"action": "speak", "text": "Volume toggled."}
            ], "mute")

        # ---- SCREENSHOT ----
        if re.search(r"(screenshot|capture screen|take a screenshot|screen capture|print screen)", c):
            return ActionPlan([
                {"action": "system", "command": "screenshot"},
                {"action": "speak", "text": "Screenshot saved to your desktop."}
            ], "screenshot")

        # ---- LOCK WORKSTATION ----
        if re.search(r"(lock (pc|computer|workstation|screen)|lock my pc)", c):
            return ActionPlan([
                {"action": "speak", "text": "Locking workstation."},
                {"action": "system", "command": "lock"}
            ], "lock")

        # ---- SCROLLING ----
        if re.search(r"scroll down|page down", c):
            return ActionPlan([{"action": "scroll", "clicks": -500}], "scroll down")
        if re.search(r"scroll up|page up", c):
            return ActionPlan([{"action": "scroll", "clicks": 500}], "scroll up")
        if re.search(r"scroll (to |all the way )?top", c):
            return ActionPlan([{"action": "hotkey", "keys": ["ctrl", "home"]}], "scroll top")
        if re.search(r"scroll (to |all the way )?bottom", c):
            return ActionPlan([{"action": "hotkey", "keys": ["ctrl", "end"]}], "scroll bottom")

        # ---- CLIPBOARD ACTIONS ----
        if re.search(r"^copy( that| this| all)?$", c):
            return ActionPlan([
                {"action": "hotkey", "keys": ["ctrl", "c"]},
                {"action": "speak", "text": "Copied."}
            ], "copy")
        if re.search(r"^paste$", c):
            return ActionPlan([
                {"action": "hotkey", "keys": ["ctrl", "v"]},
                {"action": "speak", "text": "Pasted."}
            ], "paste")
        if re.search(r"^select all$", c):
            return ActionPlan([{"action": "hotkey", "keys": ["ctrl", "a"]}], "select all")
        if re.search(r"^undo$", c):
            return ActionPlan([{"action": "hotkey", "keys": ["ctrl", "z"]}], "undo")
        if re.search(r"^redo$", c):
            return ActionPlan([{"action": "hotkey", "keys": ["ctrl", "y"]}], "redo")
        if re.search(r"^save( this| file)?$", c):
            return ActionPlan([
                {"action": "hotkey", "keys": ["ctrl", "s"]},
                {"action": "speak", "text": "Saved."}
            ], "save")

        # ---- WINDOW MANAGEMENT ----
        if re.search(r"minimize all|show desktop|go to desktop", c):
            return ActionPlan([
                {"action": "hotkey", "keys": ["win", "d"]},
                {"action": "speak", "text": "Desktop shown."}
            ], "show desktop")
        if re.search(r"task manager", c):
            return ActionPlan([
                {"action": "hotkey", "keys": ["ctrl", "shift", "esc"]},
                {"action": "speak", "text": "Task Manager opened."}
            ], "task manager")

        # ---- FOLDER CREATION (Actionable OS execution) ----
        m = re.match(r"(?:create|make|new)\s+(?:a\s+)?folder\s+(?:named|called\s+)?(.+)", c)
        if m:
            fname = m.group(1).strip().strip("'\"")
            # Create on Desktop
            desktop = Path(os.environ.get("USERPROFILE", "C:")) / "Desktop"
            target_path = str(desktop / fname)
            return ActionPlan([
                {"action": "shell", "command": f'powershell -Command New-Item -ItemType Directory -Path "{target_path}" -Force'},
                {"action": "speak", "text": f"Created folder {fname} on your desktop."}
            ], f"create folder {fname}")

        # ---- NEW TEXT FILE (Actionable OS execution) ----
        m = re.match(r"(?:create|make|new)\s+(?:a\s+)?(?:text\s+)?file\s+(?:named|called\s+)?(.+)", c)
        if m:
            tname = m.group(1).strip().strip("'\"")
            if not tname.endswith(".txt"):
                tname += ".txt"
            desktop = Path(os.environ.get("USERPROFILE", "C:")) / "Desktop"
            target_path = str(desktop / tname)
            return ActionPlan([
                {"action": "shell", "command": f'powershell -Command New-Item -ItemType File -Path "{target_path}" -Force'},
                {"action": "open_app", "target": target_path},
                {"action": "speak", "text": f"Created and opened {tname}."}
            ], f"create file {tname}")

        # ---- MULTI-STEP: Chrome Search ----
        m = re.match(r"(?:open|launch)?\s*chrome\s+and\s+(?:search|google|look up)\s+(?:for\s+)?(.+)", c)
        if not m:
            m = re.match(r"(?:search|google|look up)\s+(.+?)(?:\s+(?:in|on|using)\s+chrome)?$", c)
        if m:
            query = m.group(1).strip()
            return ActionPlan([
                {"action": "open_app", "target": "chrome"},
                {"action": "wait", "seconds": 1.2},
                {"action": "hotkey", "keys": ["ctrl", "t"]},
                {"action": "wait", "seconds": 0.2},
                {"action": "type_text", "text": f"https://www.google.com/search?q={query.replace(' ', '+')}", "enter": True},
                {"action": "speak", "text": f"Searching Google for {query}."}
            ], "chrome search")

        # ---- MULTI-STEP: YouTube Search & Play ----
        m = re.match(r"(?:play|open|search|watch)\s+(.+?)\s+(?:on\s+)?youtube", c)
        if not m:
            m = re.match(r"youtube\s+(.+)", c)
        if m:
            query = m.group(1).strip()
            return ActionPlan([
                {"action": "open_app", "target": "chrome"},
                {"action": "wait", "seconds": 1.2},
                {"action": "hotkey", "keys": ["ctrl", "t"]},
                {"action": "wait", "seconds": 0.2},
                {"action": "type_text", "text": f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}", "enter": True},
                {"action": "speak", "text": f"Playing {query} on YouTube."}
            ], "youtube search")

        # ---- MULTI-STEP: Type in Notepad ----
        m = re.match(r"type\s+(?:this\s+)?(?:text|paragraph|message)?\s*(?:in|into|on)?\s*notepad:?\s*(.*)", c)
        if m:
            text_to_type = m.group(1).strip() or "Voice dictation from JARVIS"
            return ActionPlan([
                {"action": "open_app", "target": "notepad"},
                {"action": "wait", "seconds": 1.0},
                {"action": "type_text", "text": text_to_type, "enter": False},
                {"action": "speak", "text": "Pasted into Notepad."}
            ], "type in notepad")

        # ---- HANDY DIRECT TYPING: "type X" into whichever window is open ----
        m = re.match(r"^type\s+(.+)", c)
        if m:
            text_to_type = m.group(1).strip()
            return ActionPlan([
                {"action": "type_text", "text": text_to_type, "enter": False},
                {"action": "speak", "text": "Typed."}
            ], "handy direct typing")

        # ---- CAD & ENGINEERING SOFTWARE ----
        if "solidworks" in c:
            return ActionPlan([
                {"action": "open_app", "target": "solidworks"},
                {"action": "speak", "text": "Launching SolidWorks."}
            ], "solidworks")

        if "autocad" in c:
            if "new" in c or "drawing" in c:
                return ActionPlan([
                    {"action": "open_app", "target": "autocad"},
                    {"action": "wait", "seconds": 3.0},
                    {"action": "hotkey", "keys": ["ctrl", "n"]},
                    {"action": "speak", "text": "Opening AutoCAD with a new drawing."}
                ], "autocad new")
            return ActionPlan([
                {"action": "open_app", "target": "autocad"},
                {"action": "speak", "text": "Launching AutoCAD."}
            ], "autocad")

        # ---- CLOSE ACTIONS ----
        m = re.match(r"close\s+(.+)", c)
        if m:
            target = m.group(1).strip()
            if target in ["window", "this window", "active window", "this", "it"]:
                return ActionPlan([
                    {"action": "hotkey", "keys": ["alt", "f4"]},
                    {"action": "speak", "text": "Closed active window."}
                ], "close active window")
            if target in ["tab", "this tab"]:
                return ActionPlan([
                    {"action": "hotkey", "keys": ["ctrl", "w"]},
                    {"action": "speak", "text": "Tab closed."}
                ], "close tab")
            return ActionPlan([
                {"action": "close_window", "target": target},
                {"action": "speak", "text": f"Closing {target}."}
            ], f"close {target}")

        # ---- SWITCH WINDOW ----
        m = re.match(r"(?:switch|go)\s+to\s+(.+)", c)
        if m:
            target = m.group(1).strip()
            return ActionPlan([
                {"action": "focus_window", "target": target},
                {"action": "speak", "text": f"Switching to {target}."}
            ], f"switch to {target}")

        # ---- OPEN/LAUNCH APP (Generic) ----
        m = re.match(r"(?:open|launch|start|run)\s+(.+?)$", c)
        if m:
            target = m.group(1).strip()
            skip_words = {"this", "that", "it"}
            if target not in skip_words:
                return ActionPlan([
                    {"action": "open_app", "target": target},
                    {"action": "speak", "text": f"Opening {target}."}
                ], f"open {target}")

        # ---- FACTUAL QUESTIONS ONLY (Allowed verbal responses) ----
        if re.search(r"(what('s| is) the time|current time|what time is it)", c):
            import datetime
            t = datetime.datetime.now().strftime("%I:%M %p")
            return ActionPlan([{"action": "speak", "text": f"The time is {t}."}], "time")

        if re.search(r"(what('s| is) (today|the date)|current date|what day is it)", c):
            import datetime
            d = datetime.datetime.now().strftime("%A, %B %d, %Y")
            return ActionPlan([{"action": "speak", "text": f"Today is {d}."}], "date")

        if re.search(r"^(hello|hi|hey|good morning|good evening)", c):
            return ActionPlan([{"action": "speak", "text": f"Online and ready, {config.user_name}."}], "greeting")

        if re.search(r"^(stop|cancel|halt|abort)$", c):
            return ActionPlan([{"action": "speak", "text": "Automation halted."}], "stop")

        return None

    # ------------------------------------------------------------------ #
    # Autonomous LLM Planning (Gemini)                                   #
    # ------------------------------------------------------------------ #
    def _try_llm_planning(self, cmd: str) -> ActionPlan | None:
        if not config.gemini_api_key and not config.openai_api_key:
            return None

        try:
            windows = [w["title"] for w in window_manager.get_open_windows()][:6]
        except Exception:
            windows = []

        system_prompt = f"""You are the autonomous AI execution brain of JARVIS, a Windows desktop assistant.
Convert the user command into a JSON array of executable desktop actions.

CRITICAL MANDATES:
1. NEVER explain how to do the task. DO NOT act as a teacher or conversational guide.
2. YOU MUST EXECUTE THE TASK ON WINDOWS.
3. Every plan must perform the concrete steps (open_app, click_element, type_text, hotkey, press_key, scroll, system, shell) followed by a brief confirmation speak action.
4. Output ONLY a valid JSON array. Zero markdown, zero formatting, zero conversational prose.

Active Windows: {windows}

Available Actions:
- {{"action": "open_app", "target": "app_or_file_name"}}
- {{"action": "focus_window", "target": "window_title"}}
- {{"action": "close_window", "target": "window_title"}}
- {{"action": "click_element", "name": "button_name"}}
- {{"action": "type_text", "text": "text_to_type", "enter": true}}
- {{"action": "hotkey", "keys": ["ctrl", "s"]}}
- {{"action": "press_key", "key": "enter"}}
- {{"action": "scroll", "clicks": -500}}
- {{"action": "wait", "seconds": 1.0}}
- {{"action": "system", "command": "volume|screenshot|lock", "direction": "up|down"}}
- {{"action": "shell", "command": "safe powershell or cmd command"}}
- {{"action": "speak", "text": "Brief confirmation message"}}

User Command: {cmd}"""

        try:
            if config.gemini_api_key:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=config.gemini_api_key)
                response = client.models.generate_content(
                    model=config.gemini_model,
                    contents=system_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0
                    )
                )
                text = response.text.strip()
                text = re.sub(r"^```(?:json)?\s*", "", text)
                text = re.sub(r"\s*```$", "", text)
                steps = json.loads(text)
                if isinstance(steps, list) and len(steps) > 0:
                    logger.info(f"[Brain] Autonomous LLM generated {len(steps)} executable steps.")
                    return ActionPlan(steps=steps, explanation="Autonomous Gemini Action Plan")

        except Exception as e:
            logger.warning(f"[Brain] LLM planning error: {e}")

        return None


brain = AIBrain()
