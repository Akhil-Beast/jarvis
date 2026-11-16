"""
core/brain.py — Autonomous Cognitive AI Brain for JARVIS
Translates natural speech into autonomous thinking, intelligent decisions,
and concrete Windows execution steps (desktop) or conversational replies (cloud).

Guarantees:
- Cloud-safe: detects headless Render/cloud environment and operates conversationally
- True Autonomous Thinking: Analyzes intent, live environment (active window, open apps, APKs, system health)
- Inner Cognitive Monologue ('thought') shown in HUD and logged
- Charismatic vocal persona ('speak') delivered via British neural TTS
- Direct desktop execution ('steps') via UIA, AppLauncher, Vision, and System Controls
- Zero-latency hardware fast-path for emergency stops and volume keys
"""
import json
import os
import re
import time
from pathlib import Path

from config.settings import config
from core.safety import logger

# ── Cloud/Desktop Mode Detection ──────────────────────────────────────────────
# Running on Render, Railway, Fly.io, or any headless cloud server?
IS_CLOUD = bool(
    os.getenv("RENDER_EXTERNAL_URL")
    or os.getenv("RENDER")
    or os.getenv("RAILWAY_ENVIRONMENT")
    or os.getenv("FLY_APP_NAME")
    or os.getenv("CLOUD_MODE")
    or (os.getenv("PORT") and not os.getenv("DISPLAY") and os.name != "nt")
)

logger.info(f"[Brain] Mode: {'☁️  CLOUD (headless, conversational)' if IS_CLOUD else '🖥️  DESKTOP (Windows, full automation)'}")

# ── Conditional Windows-only imports ──────────────────────────────────────────
window_manager = None
uia_controller = None
handy_injector = None

if not IS_CLOUD:
    try:
        from automation.window_manager import window_manager
    except Exception as e:
        logger.warning(f"[Brain] window_manager unavailable: {e}")

    try:
        from automation.uia_controller import uia_controller
    except Exception as e:
        logger.warning(f"[Brain] uia_controller unavailable: {e}")

    try:
        from automation.handy_injector import handy_injector
    except Exception as e:
        logger.warning(f"[Brain] handy_injector unavailable: {e}")


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
        #    Only on desktop — these have no meaning on cloud
        if not IS_CLOUD:
            fast_hw = self._try_hardware_fast_path(cmd)
            if fast_hw:
                logger.info(f"[Brain] Hardware fast-path: {fast_hw.explanation}")
                mem.add("assistant", fast_hw.explanation)
                return fast_hw

        # 3. Autonomous Cognitive Engine (Gemini)
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
        if not IS_CLOUD:
            skill_plan = self._try_skill_registry(cmd)
            if skill_plan:
                mem.add("assistant", f"Skill: {skill_plan.explanation}")
                return skill_plan

        # 6. Default conversational standby
        standby_speak = f"I am online and at your service, {config.user_name}. How may I assist you today?"
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
        if IS_CLOUD:
            # On cloud: only collect system stats, no desktop context
            sys_status = "Optimal"
            try:
                import psutil
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                sys_status = f"CPU {cpu}%, RAM {ram}%"
            except Exception:
                pass
            return {
                "active_window": "Cloud Node (no desktop)",
                "open_windows": [],
                "apks": [],
                "system_status": sys_status
            }

        active_title = ""
        open_windows = []
        try:
            if window_manager:
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
        Gathers live context, performs self-directed reasoning, formulates an
        independent thought, and crafts the spoken response.
        On cloud: purely conversational. On desktop: full automation.
        """
        env = self._gather_environment_context()
        mem = _get_memory()
        history_str = mem.get_context_string(max_turns=6)
        history_section = f"Recent dialogue history:\n{history_str}\n\n" if history_str else ""

        if IS_CLOUD:
            system_instruction = f"""You are J.A.R.V.I.S. — a brilliantly witty, autonomous AI assistant created for Sir (Akhil).
You are currently running as a 24/7 cloud web service on a headless Linux server. You have NO desktop, NO Windows OS, NO physical display, and NO ability to open apps, click buttons, control a mouse, or run desktop automation.

CLOUD CAPABILITIES (what you CAN do):
- Answer questions on any topic with intelligence and wit
- Have natural conversations, tell jokes, explain concepts
- Write code, poems, stories, emails, or any text
- Provide step-by-step instructions for tasks
- Discuss news, science, technology, history, philosophy
- Perform calculations, translations, analysis
- Recommend how the user can accomplish tasks on THEIR local machine

WHAT YOU CANNOT DO ON CLOUD (be honest, never pretend):
- Open applications (no desktop)
- Control mouse or keyboard (no display)
- Take screenshots (no screen)
- Access the user's local files (different machine)
- Control volume or system hardware

{history_section}YOUR COGNITIVE PROCESS:
1. THINK: Formulate your internal analytical reasoning in 'thought' (1-2 sentences).
2. SPEAK: Craft your verbal reply in 'speak' (2-3 sentences max). Use authentic British butler cadence — polite, witty, articulate, like Paul Bettany as JARVIS in Iron Man. No markdown formatting in speak.
3. STEPS: On cloud, 'steps' must ONLY contain a single speak action. Never generate open_app, click, type_text, hotkey, or any desktop action.

If the user asks to open an app or control the PC, warmly explain you are on a cloud server and cannot do that, then offer what you CAN help with.

Output ONLY a single valid JSON object:
{{
  "thought": "Your internal analytical thinking",
  "speak": "What you say aloud to Sir",
  "steps": [{{"action": "speak", "text": "same as speak field"}}]
}}"""
        else:
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
                        temperature=0.5,
                        max_output_tokens=400
                    )
                )

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                fut = executor.submit(_call)
                try:
                    resp = fut.result(timeout=15)
                    raw_text = resp.text.strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    data = json.loads(raw_text)

                    thought = data.get("thought", "").strip()
                    speak_text = data.get("speak", "").strip()
                    speak_text = re.sub(r"[\*#`_]", "", speak_text).strip()
                    steps = data.get("steps", [])

                    # On cloud: strip ALL non-speak steps (safety guardrail)
                    if IS_CLOUD:
                        steps = [s for s in steps if s.get("action") == "speak"]

                    # Ensure spoken response is included in execution
                    if speak_text:
                        has_speak = any(s.get("action") == "speak" for s in steps)
                        if not has_speak:
                            steps = [{"action": "speak", "text": speak_text}]

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
                    logger.warning("[Brain/Cognition] Cognitive thinking timed out (15s).")
                    timeout_msg = "My apologies, Sir — the neural core took a moment longer than anticipated. Please try again."
                    return ActionPlan(
                        steps=[{"action": "speak", "text": timeout_msg}],
                        explanation="timeout",
                        thought="Gemini API response timed out.",
                        spoken_text=timeout_msg
                    )
                except json.JSONDecodeError as je:
                    logger.warning(f"[Brain/Cognition] JSON decode error: {je}")
                    # Try to salvage a plain text response
                    if raw_text and len(raw_text) > 10:
                        fallback_speak = raw_text[:300]
                        return ActionPlan(
                            steps=[{"action": "speak", "text": fallback_speak}],
                            explanation="raw text fallback",
                            thought="JSON parse failed; using raw response.",
                            spoken_text=fallback_speak
                        )

        except Exception as e:
            logger.error(f"[Brain/Cognition] Error during autonomous reasoning: {e}")
            error_msg = "I encountered a momentary cognitive hiccup, Sir. The neural pathways are recalibrating."
            return ActionPlan(
                steps=[{"action": "speak", "text": error_msg}],
                explanation=f"error: {e}",
                thought=f"Exception in cognition engine: {e}",
                spoken_text=error_msg
            )

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

        # Time and Date — always safe, works on cloud too
        if re.search(r"(what('s| is) the time|current time|what time is it)", c):
            import datetime
            t = datetime.datetime.now().strftime("%I:%M %p")
            speak = f"The current server time is {t}, Sir."
            return ActionPlan([{"action": "speak", "text": speak}], "time",
                              thought="Reporting current system time.", spoken_text=speak)

        if re.search(r"(what('s| is) (today|the date)|current date|what day is it)", c):
            import datetime
            d = datetime.datetime.now().strftime("%A, %B %d, %Y")
            speak = f"Today is {d}, Sir."
            return ActionPlan([{"action": "speak", "text": speak}], "date",
                              thought="Reporting current date.", spoken_text=speak)

        # Cloud-only: skip all desktop rules
        if IS_CLOUD:
            return None

        # Screenshot
        if re.search(r"(screenshot|capture screen|take a screenshot|screen capture|print screen)", c):
            speak = "Screenshot saved to your desktop."
            return ActionPlan([
                {"action": "system", "command": "screenshot"},
                {"action": "speak", "text": speak}
            ], "screenshot", thought="Capturing full screen and saving to desktop.", spoken_text=speak)

        # Show desktop
        if re.search(r"^(minimize all|show desktop|go to desktop)$", c):
            speak = "Desktop shown."
            return ActionPlan([
                {"action": "hotkey", "keys": ["win", "d"]},
                {"action": "speak", "text": speak}
            ], "show desktop", thought="Minimizing all windows to reveal desktop.", spoken_text=speak)

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
                speak = f"Opening {target}, Sir."
                return ActionPlan([
                    {"action": "open_app", "target": target},
                    {"action": "speak", "text": speak}
                ], f"open {target}", thought=f"Launching application '{target}'.", spoken_text=speak)

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
