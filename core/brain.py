"""
core/brain.py — Autonomous Desktop Action Planning Engine
Translates user voice input into concrete Windows execution steps.

Guarantees:
- NEVER explains how to do a task verbally; ALWAYS executes the action on the PC.
- Strips conversational wrappers ("how to", "tell me how to", "can you", "please").
- Instant local rules for common desktop actions (zero latency).
- Direct Handy-style text injection for dictation into active apps.
- Autonomous Gemini execution planner with conversation memory for complex instructions.
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

# Lazy import to avoid circular dependency — memory is a sibling module
def _get_memory():
    from core.memory import memory
    return memory


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

        # Record user utterance in memory
        mem = _get_memory()
        mem.add("user", raw_cmd)

        # 1. Fast local execution rules (instant, zero network latency)
        local_plan = self._try_local_rules(cmd)
        if local_plan:
            logger.info(f"[Brain] Matched local action rule ({local_plan.explanation})")
            mem.add("assistant", local_plan.explanation)
            return local_plan

        # 1.5 Skill registry — modular skills before hitting Gemini
        skill_plan = self._try_skill_registry(cmd)
        if skill_plan:
            mem.add("assistant", f"Skill: {skill_plan.explanation}")
            return skill_plan

        # 2. Conversational Thinking & Voice Reply: Communicate naturally
        if self._is_conversational_query(raw_cmd):
            logger.info(f"[Brain] Conversational query detected — activating JARVIS thinking...")
            thought_plan = self._think_and_converse(raw_cmd)
            if thought_plan:
                mem.add("assistant", thought_plan.explanation)
                return thought_plan

        # 3. Autonomous LLM desktop action planner (Gemini)
        llm_plan = self._try_llm_planning(cmd)
        if llm_plan and not self._is_passive_tutorial(llm_plan, cmd):
            mem.add("assistant", f"Executed: {llm_plan.explanation}")
            return llm_plan

        # 4. Smart execution fallback — open/run target directly
        shell_plan = self._smart_shell_fallback(cmd)
        if shell_plan:
            mem.add("assistant", shell_plan.explanation)
            return shell_plan

        # 5. Conversational Fallback: Think and reply in voice rather than dumping user into browser!
        conversational_fallback = self._think_and_converse(raw_cmd)
        if conversational_fallback:
            mem.add("assistant", conversational_fallback.explanation)
            return conversational_fallback

        # 6. Final conversational voice standby
        mem.add("assistant", "At your service")
        return ActionPlan(
            steps=[{"action": "speak", "text": f"I am at your service, {config.user_name}. How may I assist you?"}],
            explanation="Conversational standby"
        )

    # ------------------------------------------------------------------ #
    # Skill Registry Dispatch                                             #
    # ------------------------------------------------------------------ #
    def _try_skill_registry(self, cmd: str) -> ActionPlan | None:
        try:
            from skills import skill_registry
            skill = skill_registry.find_skill(cmd)
            if skill:
                logger.info(f"[Brain] Dispatching to skill: {skill.name}")
                steps = skill.execute(cmd)
                return ActionPlan(steps=steps, explanation=f"Skill:{skill.name}")
        except Exception as e:
            logger.warning(f"[Brain] Skill registry error: {e}")
        return None

    # ------------------------------------------------------------------ #
    # Conversational Thinking & Natural Voice Reply                      #
    # ------------------------------------------------------------------ #
    def _is_conversational_query(self, cmd: str) -> bool:
        """Determines if the command is a conversational query, thought request, or chat."""
        c = cmd.lower().strip()

        # If user explicitly starts with a concrete action verb, it's NOT purely conversational
        action_verbs = [
            "open ", "launch ", "start ", "close ", "kill ", "click ", "double click ",
            "type ", "press ", "scroll ", "volume ", "mute ", "unmute ", "screenshot",
            "lock ", "shutdown", "restart", "create folder", "create file", "new folder",
            "new file", "delete file", "install apk", "install app", "switch to "
        ]
        if any(c.startswith(a) for a in action_verbs):
            return False

        conv_patterns = [
            r"^(?:what|why|how|who|when|where|is|are|can|could|would|do|does|will|should)\b",
            r"\b(?:think|opinion|believe|feel|suggest|recommend|advise|explain|describe)\b",
            r"\b(?:joke|riddle|story|poem|quote|trivia|meaning|definition)\b",
            r"^(?:hi|hello|hey|good\s+(?:morning|afternoon|evening)|howdy)\b",
            r"^(?:thank\s+you|thanks|good\s+job|well\s+done)\b",
            r"\b(?:who\s+(?:are\s+you|made\s+you)|your\s+name|about\s+yourself|tell\s+me\s+about\s+you)\b",
            r"\b(?:talk\s+to\s+me|converse|chat|are\s+you\s+there|you\s+listening)\b",
        ]
        return any(re.search(p, c) for p in conv_patterns)

    def _think_and_converse(self, text: str) -> ActionPlan | None:
        """
        JARVIS Conversational Thinking Engine:
        Uses Gemini to think, analyze context, and generate an articulate, witty,
        British-butler-style vocal reply.
        """
        if not config.gemini_api_key:
            return ActionPlan(
                steps=[{"action": "speak", "text": "I am standing by, Sir. Please configure my Gemini API key to enable my conversational faculties."}],
                explanation="No Gemini API Key"
            )

        mem = _get_memory()
        context_str = mem.get_context_string(max_turns=6)
        context_section = f"Recent conversation dialogue:\n{context_str}\n\n" if context_str else ""

        system_instruction = f"""You are J.A.R.V.I.S., the highly intelligent, sophisticated, and witty AI companion and personal assistant to Sir (Akhil).
Tone & Cadence:
- Authentic British butler persona (like Paul Bettany's J.A.R.V.I.S. in Iron Man).
- Always address the user politely as 'Sir'.
- Speak with intelligence, warmth, understated dry humor, and supreme competence.
- Provide thoughtful, accurate, and insightful answers.
- Keep responses concise (2 to 3 sentences max) so voice playback is natural and conversational.
- NEVER use markdown formatting (no asterisks, bolding, bullet points, numbers, hashtags, or code blocks). Output clean, spoken English."""

        try:
            from google import genai
            from google.genai import types
            import concurrent.futures

            client = genai.Client(api_key=config.gemini_api_key)

            def _call():
                return client.models.generate_content(
                    model=config.gemini_model,
                    contents=f"{context_section}User: {text}\nJARVIS:",
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.7,
                        max_output_tokens=220
                    )
                )

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                fut = executor.submit(_call)
                try:
                    resp = fut.result(timeout=6)
                    reply = resp.text.strip()
                    # Clean any trailing markdown or quotes
                    reply = re.sub(r"[\*#`_]", "", reply).strip()
                    if reply:
                        logger.info(f"[Brain/Converse] Thought reply: '{reply}'")
                        return ActionPlan(
                            steps=[{"action": "speak", "text": reply}],
                            explanation=f"Conversational: {reply[:45]}..."
                        )
                except concurrent.futures.TimeoutError:
                    logger.warning("[Brain/Converse] Conversational thinking timed out.")

        except Exception as e:
            logger.error(f"[Brain/Converse] Thinking error: {e}")

        return None

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

        # ---- SCREEN VISION & WHAT'S ON SCREEN ----
        if re.search(r"(what('s| is) on (my |the )?screen|look at (my |the )?screen|see (my |the )?screen|can you see (my |the )?screen|read (my |the )?screen|analyze (my |the )?screen|describe (my |the )?screen|what do you see)", c):
            return ActionPlan([
                {"action": "vision_inspect", "prompt": "Describe what is currently visible on this computer screen. Highlight any open applications, APK files, windows, and icons."}
            ], "vision inspect screen")

        # ---- APK VISION & SCREEN INTERACTION ----
        if re.search(r"(do you see (the |any )?apk|find (the |any )?apk on (the |my )?screen|where is the apk|is there an apk|look for (the |an )?apk)", c):
            return ActionPlan([
                {"action": "vision_inspect", "prompt": "Examine this screen specifically for any APK files, Android packages, or app installers. State their exact file names and locations."}
            ], "vision find apk on screen")

        # APK: Find / Show all APKs
        if re.search(r"^(show|find|list|where (are|is)|locate)\s+(?:all\s+)?(?:the\s+)?apks?$", c) or re.search(r"^apks?$", c):
            return ActionPlan([
                {"action": "apk_action", "command": "find", "target": ""}
            ], "find all apks")

        # APK: Install
        m_inst = re.match(r"(?:install|sideload)\s+(?:the\s+)?(?:apk|app)?\s*(.*)", c)
        if m_inst and ("apk" in c or "install" in c):
            apk_target = m_inst.group(1).strip()
            return ActionPlan([
                {"action": "apk_action", "command": "install", "target": apk_target}
            ], f"install apk {apk_target}")

        # APK: Inspect / Details
        m_insp = re.match(r"(?:inspect|check|details (?:of|for|on)|info (?:on|for))\s+(?:the\s+)?apk\s*(.*)", c)
        if m_insp:
            apk_target = m_insp.group(1).strip()
            return ActionPlan([
                {"action": "apk_action", "command": "inspect", "target": apk_target}
            ], f"inspect apk {apk_target}")

        # APK: Open folder / Show in Explorer
        m_opn_apk = re.match(r"(?:open|show)\s+(?:the\s+)?apk\s*(.*)", c)
        if m_opn_apk:
            apk_target = m_opn_apk.group(1).strip()
            return ActionPlan([
                {"action": "apk_action", "command": "open", "target": apk_target}
            ], f"open apk {apk_target}")

        # ---- SCREEN TARGET CLICKING (UIA + VISION COORDINATES) ----
        m_dclick = re.match(r"(?:double\s+click|doubleclick)\s+(?:on\s+)?(?:the\s+)?(.+)", c)
        if m_dclick:
            target = m_dclick.group(1).strip()
            return ActionPlan([
                {"action": "click_screen_target", "target": target, "click_type": "double"}
            ], f"double click {target}")

        m_rclick = re.match(r"(?:right\s+click|rightclick)\s+(?:on\s+)?(?:the\s+)?(.+)", c)
        if m_rclick:
            target = m_rclick.group(1).strip()
            return ActionPlan([
                {"action": "click_screen_target", "target": target, "click_type": "right"}
            ], f"right click {target}")

        m_click = re.match(r"^click\s+(?:on\s+)?(?:the\s+)?(.+)", c)
        if m_click:
            target = m_click.group(1).strip()
            if target not in ["here", "now", "it", "this"]:
                return ActionPlan([
                    {"action": "click_screen_target", "target": target, "click_type": "single"}
                ], f"click {target}")

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
    # Autonomous LLM Planning (Gemini) with Memory                       #
    # ------------------------------------------------------------------ #
    def _try_llm_planning(self, cmd: str) -> ActionPlan | None:
        if not config.gemini_api_key and not config.openai_api_key:
            return None

        try:
            windows = [w["title"] for w in window_manager.get_open_windows()][:6]
        except Exception:
            windows = []

        # Pull recent conversation context
        mem = _get_memory()
        context_str = mem.get_context_string(max_turns=6)
        context_section = f"\nRecent conversation:\n{context_str}\n" if context_str else ""

        system_prompt = f"""You are the autonomous AI execution brain of JARVIS, a Windows desktop assistant.
Convert the user command into a JSON array of executable desktop actions.

CRITICAL MANDATES:
1. NEVER explain how to do the task. DO NOT act as a teacher or conversational guide.
2. YOU MUST EXECUTE THE TASK ON WINDOWS.
3. Every plan must perform the concrete steps (open_app, click_element, type_text, hotkey, press_key, scroll, system, shell) followed by a brief confirmation speak action.
4. Output ONLY a valid JSON array. Zero markdown, zero formatting, zero conversational prose.
{context_section}
Active Windows: {windows}

Available Actions:
- {{"action": "open_app", "target": "app_or_file_name"}}
- {{"action": "focus_window", "target": "window_title"}}
- {{"action": "close_window", "target": "window_title"}}
- {{"action": "vision_inspect", "prompt": "what to look for on screen or finding APKs"}}
- {{"action": "click_screen_target", "target": "element or APK name to click on screen", "click_type": "single|double|right"}}
- {{"action": "apk_action", "command": "find|inspect|install|open", "target": "optional_apk_name"}}
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
                import concurrent.futures

                client = genai.Client(api_key=config.gemini_api_key)

                def _call_gemini():
                    return client.models.generate_content(
                        model=config.gemini_model,
                        contents=system_prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.0,
                            max_output_tokens=512
                        )
                    )

                # 8-second hard timeout — fast fallback if network lags
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_call_gemini)
                    try:
                        response = future.result(timeout=8)
                    except concurrent.futures.TimeoutError:
                        logger.warning("[Brain] Gemini call timed out after 8s — using local fallback.")
                        return None

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
