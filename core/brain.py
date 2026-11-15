"""
core/brain.py — Autonomous Cognitive AI Brain for JARVIS
Translates natural speech into autonomous thinking, intelligent decisions,
and concrete Windows execution steps.

Guarantees:
- True Autonomous Thinking: Analyzes intent, live environment (active window, open apps, APKs, system health)
- Inner Cognitive Monologue ('thought') shown in HUD and logged
- Charismatic vocal persona ('speak') delivered via British neural TTS
- Direct desktop execution ('steps') via UIA, AppLauncher, Vision, and System Controls
- Zero-latency hardware fast-path for emergency stops and volume keys
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


def _get_memory():
    from core.memory import memory
    return memory


class ActionPlan:
    """Standardized multi-step action representation with autonomous cognitive reasoning."""

    def __init__(self, steps: list[dict], explanation: str = "", thought: str = "", spoken_text: str = ""):
        self.steps = steps
        self.explanation = explanation or thought
        self.thought = thought
        self.spoken_text = spoken_text


class AIBrain:
    """Autonomous Cognitive AI Brain for JARVIS."""

    def __init__(self):
        pass

    def plan_command(self, user_command: str) -> ActionPlan:
        raw_cmd = user_command.strip()
        cmd = self._normalize_intent(raw_cmd)
        logger.info(f"[Brain] Processing command: '{raw_cmd}'")

        # 1. Update conversation memory
        mem = _get_memory()
        mem.add("user", raw_cmd)

        # 2. Hardware Emergency Stop & Basic Hardware Keys (sub-millisecond fast-path)
        fast_hw = self._try_hardware_fast_path(cmd)
        if fast_hw:
            logger.info(f"[Brain] Hardware fast-path: {fast_hw.explanation}")
            mem.add("assistant", fast_hw.explanation)
            return fast_hw

        # 3. Autonomous Cognitive Engine (Gemini 3.5 Flash-Lite)
        #    Thinks by itself with live environmental awareness and self-directed decision making
        if config.gemini_api_key:
            cog_plan = self._autonomous_cognition(raw_cmd)
            if cog_plan:
                mem.add("assistant", cog_plan.spoken_text or cog_plan.thought or cog_plan.explanation)
                return cog_plan

        # 4. Local action rules fallback (if offline or API error)
        local_plan = self._try_local_rules(cmd)
        if local_plan:
            logger.info(f"[Brain] Fallback local rule: {local_plan.explanation}")
            mem.add("assistant", local_plan.explanation)
            return local_plan

        # 5. Skill registry fallback
        skill_plan = self._try_skill_registry(cmd)
        if skill_plan:
            mem.add("assistant", f"Skill: {skill_plan.explanation}")
            return skill_plan

        # 6. Default conversational standby
        standby_speak = f"I am online and at your service, {config.user_name}."
        mem.add("assistant", standby_speak)
        return ActionPlan(
            steps=[{"action": "speak", "text": standby_speak}],
            explanation="Standby",
            thought="System operating in standby mode.",
            spoken_text=standby_speak
        )

    # ------------------------------------------------------------------ #
    # Live Environmental Perception & Context Gathering                  #
    # ------------------------------------------------------------------ #
    def _gather_environment_context(self) -> dict:
        """Collects live PC context so JARVIS has situational awareness."""
        active_title = ""
        open_windows = []
        try:
            active_title = window_manager.get_active_window_title()
            open_windows = [w["title"] for w in window_manager.get_open_windows()][:8]
        except Exception:
            pass

        apk_summary = []
        try:
            from automation.screen_vision import screen_vision
            apks = screen_vision.find_all_apks()
            apk_summary = [f"{a['app_name']} ({a['filename']}, pkg={a['package_name']})" for a in apks[:3]]
        except Exception:
            pass

        sys_status = "Optimal"
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            sys_status = f"CPU {cpu}%, RAM {ram}%"
        except Exception:
            pass

        return {
            "active_window": active_title or "Desktop",
            "open_windows": open_windows,
            "apks": apk_summary,
            "system_status": sys_status
        }

    # ------------------------------------------------------------------ #
    # Autonomous Cognitive Thinking Engine                               #
    # ------------------------------------------------------------------ #
    def _autonomous_cognition(self, user_text: str) -> ActionPlan | None:
        """
        Core Thinking Engine:
        Gathers live PC context, performs self-directed reasoning, formulates an
        independent thought, decides on computer actions, and crafts the spoken response.
        """
        env = self._gather_environment_context()
        mem = _get_memory()
        history_str = mem.get_context_string(max_turns=6)
        history_section = f"Recent dialogue history:\n{history_str}\n\n" if history_str else ""

        system_instruction = f"""You are J.A.R.V.I.S., the autonomous, self-thinking AI personal desktop assistant for Sir (Akhil).
You possess your own analytical intellect, autonomous judgment, and situational awareness.

LIVE ENVIRONMENT CONTEXT:
- Active Foreground Window: {env['active_window']}
- Visible Open Windows: {env['open_windows']}
- Discovered APKs on Device/Storage: {env['apks']}
- System Health Diagnostics: {env['system_status']}

{history_section}YOUR COGNITIVE PROCESS:
1. THINK ON YOUR OWN FIRST: Analyze what Sir is asking or observing. Formulate your internal analytical thought process in 'thought' (explain your reasoning, contextual assessment, and chosen strategy).
2. SPOKEN REPLY: Craft your verbal response in 'speak' (2 to 3 sentences maximum, authentic British butler cadence like Paul Bettany in Iron Man, polite, witty, articulate, NO markdown formatting).
3. DESKTOP ACTIONS: If the request requires interacting with the PC, select the appropriate concrete steps ('steps'). If purely conversational, advice, or discussion, 'steps' can be empty.

Available Actions for 'steps':
- {{"action": "open_app", "target": "app_or_file_name"}}
- {{"action": "focus_window", "target": "window_title"}}
- {{"action": "close_window", "target": "window_title"}}
- {{"action": "type_text", "text": "text_to_type", "enter": true/false}}
- {{"action": "hotkey", "keys": ["ctrl", "c"]}}
- {{"action": "press_key", "key": "enter"}}
- {{"action": "scroll", "clicks": -300}}
- {{"action": "system", "command": "volume|screenshot|lock", "direction": "up|down"}}
- {{"action": "vision_inspect", "prompt": "what to look for on screen"}}
- {{"action": "click_screen_target", "target": "icon_or_element_name", "click_type": "single|double|right"}}
- {{"action": "apk_action", "command": "find|inspect|install|open", "target": "apk_name"}}
- {{"action": "shell", "command": "safe powershell command"}}

Output format:
Output ONLY a single valid JSON object:
{{
  "thought": "Your internal analytical thinking and decision-making",
  "speak": "What you say aloud to Sir",
  "steps": [array of action objects]
}}"""

        try:
            from google import genai
            from google.genai import types
            import concurrent.futures

            client = genai.Client(api_key=config.gemini_api_key)

            def _call():
                return client.models.generate_content(
                    model=config.gemini_model,
                    contents=f"User: {user_text}",
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.4,
                        max_output_tokens=400
                    )
                )

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                fut = executor.submit(_call)
                try:
                    resp = fut.result(timeout=6)
                    raw_text = resp.text.strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    data = json.loads(raw_text)

                    thought = data.get("thought", "").strip()
                    speak_text = data.get("speak", "").strip()
                    speak_text = re.sub(r"[\*#`_]", "", speak_text).strip()
                    steps = data.get("steps", [])

                    # Ensure spoken response is included in execution
                    if speak_text:
                        has_speak = any(s.get("action") == "speak" for s in steps)
                        if not has_speak:
                            steps.append({"action": "speak", "text": speak_text})

                    logger.info(f"[Brain/Cognition] Thought: '{thought}'")
                    logger.info(f"[Brain/Cognition] Spoken: '{speak_text}'")
                    logger.info(f"[Brain/Cognition] Steps ({len(steps)}): {steps}")

                    return ActionPlan(
                        steps=steps,
                        explanation=thought or speak_text,
                        thought=thought,
                        spoken_text=speak_text
                    )

                except concurrent.futures.TimeoutError:
                    logger.warning("[Brain/Cognition] Cognitive thinking timed out (6s).")
                except json.JSONDecodeError as je:
                    logger.warning(f"[Brain/Cognition] JSON decode error: {je}")

        except Exception as e:
            logger.error(f"[Brain/Cognition] Error during autonomous reasoning: {e}")

        return None

    # ------------------------------------------------------------------ #
    # Hardware Fast-Path (Instant sub-millisecond OS operations)          #
    # ------------------------------------------------------------------ #
    def _try_hardware_fast_path(self, cmd: str) -> ActionPlan | None:
        c = cmd.lower().strip()

        # Emergency stop
        if re.search(r"^(stop|cancel|halt|abort|shut up|quiet)$", c):
            return ActionPlan(
                steps=[{"action": "speak", "text": "Automation halted."}],
                explanation="Emergency Stop",
                thought="Emergency halt requested by user.",
                spoken_text="Automation halted."
            )

        # Volume controls
        for kw in ["volume up", "increase volume", "louder", "turn up volume", "raise volume", "volume higher"]:
            if kw in c:
                return ActionPlan(
                    steps=[
                        {"action": "system", "command": "volume", "direction": "up", "steps": 5},
                        {"action": "speak", "text": "Volume increased."}
                    ],
                    explanation="volume up",
                    thought="Hardware audio gain adjustment.",
                    spoken_text="Volume increased."
                )

        for kw in ["volume down", "decrease volume", "quieter", "turn down volume", "lower volume", "volume lower"]:
            if kw in c:
                return ActionPlan(
                    steps=[
                        {"action": "system", "command": "volume", "direction": "down", "steps": 5},
                        {"action": "speak", "text": "Volume decreased."}
                    ],
                    explanation="volume down",
                    thought="Hardware audio attenuation.",
                    spoken_text="Volume decreased."
                )

        if re.search(r"\b(mute|unmute|silence)\b", c):
            return ActionPlan(
                steps=[
                    {"action": "system", "command": "volume", "direction": "mute", "steps": 1},
                    {"action": "speak", "text": "Audio toggled."}
                ],
                explanation="mute",
                thought="Audio mute state toggled.",
                spoken_text="Audio toggled."
            )

        # Workstation Lock
        if re.search(r"^(lock (pc|computer|workstation|screen)|lock my pc)$", c):
            return ActionPlan(
                steps=[
                    {"action": "speak", "text": "Locking workstation."},
                    {"action": "system", "command": "lock"}
                ],
                explanation="lock",
                thought="Securing workstation via Windows lock screen.",
                spoken_text="Locking workstation."
            )

        return None

    # ------------------------------------------------------------------ #
    # Local Action Rules (Offline Fallback)                              #
    # ------------------------------------------------------------------ #
    def _try_local_rules(self, cmd: str) -> ActionPlan | None:
        c = cmd.lower().strip()

        # Screenshot
        if re.search(r"(screenshot|capture screen|take a screenshot|screen capture|print screen)", c):
            return ActionPlan([
                {"action": "system", "command": "screenshot"},
                {"action": "speak", "text": "Screenshot saved to your desktop."}
            ], "screenshot", thought="Capturing full screen and saving to desktop.")

        # Show desktop
        if re.search(r"^(minimize all|show desktop|go to desktop)$", c):
            return ActionPlan([
                {"action": "hotkey", "keys": ["win", "d"]},
                {"action": "speak", "text": "Desktop shown."}
            ], "show desktop", thought="Minimizing all windows to reveal desktop.")

        # Screen vision
        if re.search(r"(what('s| is) on (my |the )?screen|look at (my |the )?screen|see (my |the )?screen|read (my |the )?screen)", c):
            return ActionPlan([
                {"action": "vision_inspect", "prompt": "Describe what is currently visible on this computer screen. Highlight any open applications, APK files, windows, and icons."}
            ], "vision inspect screen", thought="Visual inspection of screen via Gemini Vision.")

        # APK find
        if re.search(r"^(show|find|list|where (are|is)|locate)\s+(?:all\s+)?(?:the\s+)?apks?$", c) or re.search(r"^apks?$", c):
            return ActionPlan([
                {"action": "apk_action", "command": "find", "target": ""}
            ], "find all apks", thought="Searching local and phone storage for APK files.")

        # Generic Open App
        m = re.match(r"(?:open|launch|start|run)\s+(.+?)$", c)
        if m:
            target = m.group(1).strip()
            if target not in ["this", "that", "it"]:
                return ActionPlan([
                    {"action": "open_app", "target": target},
                    {"action": "speak", "text": f"Opening {target}."}
                ], f"open {target}", thought=f"Launching application '{target}'.")

        # Time and Date
        if re.search(r"(what('s| is) the time|current time|what time is it)", c):
            import datetime
            t = datetime.datetime.now().strftime("%I:%M %p")
            return ActionPlan([{"action": "speak", "text": f"The time is {t}, Sir."}], "time", thought="Reporting current system time.")

        if re.search(r"(what('s| is) (today|the date)|current date|what day is it)", c):
            import datetime
            d = datetime.datetime.now().strftime("%A, %B %d, %Y")
            return ActionPlan([{"action": "speak", "text": f"Today is {d}, Sir."}], "date", thought="Reporting current date.")

        return None

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
                return ActionPlan(steps=steps, explanation=f"Skill:{skill.name}", thought=f"Delegated to {skill.name} skill.")
        except Exception as e:
            logger.warning(f"[Brain] Skill registry error: {e}")
        return None

    # ------------------------------------------------------------------ #
    # Intent Normalizer: Strips passive tutorial wrappers                #
    # ------------------------------------------------------------------ #
    def _normalize_intent(self, text: str) -> str:
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
        cleaned = cleaned.rstrip("?").strip()
        return cleaned


brain = AIBrain()
