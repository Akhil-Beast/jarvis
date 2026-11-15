"""
skills/web_search_skill.py — DuckDuckGo / Google web search skill.

Triggers on commands like:
  "search for X"
  "look up X"
  "what is X"
  "find information about X"
  "google X"
"""
import re
import threading
from skills.base_skill import BaseSkill
from core.safety import logger


class WebSearchSkill(BaseSkill):

    _PATTERNS = [
        r"(?:search|google|look up|find)\s+(?:for\s+|info(?:rmation)?\s+(?:about|on)\s+)?(.+)",
        r"what(?:'s| is)\s+(.+?)(?:\?)?$",
        r"who(?:'s| is)\s+(.+?)(?:\?)?$",
        r"how\s+(?:much|many|old|far|tall|big|long|fast)\s+(?:is|are|does)\s+(.+?)(?:\?)?$",
        r"tell me about\s+(.+?)(?:\?)?$",
    ]

    @property
    def name(self) -> str:
        return "WebSearch"

    @property
    def description(self) -> str:
        return "Search the web via DuckDuckGo and summarize results."

    def can_handle(self, command: str) -> bool:
        c = command.lower().strip()
        return any(re.search(p, c) for p in self._PATTERNS)

    def _extract_query(self, command: str) -> str:
        c = command.lower().strip()
        for p in self._PATTERNS:
            m = re.search(p, c)
            if m:
                return m.group(1).strip()
        return command.strip()

    def execute(self, command: str, context: dict | None = None) -> list[dict]:
        query = self._extract_query(command)
        logger.info(f"[WebSearchSkill] Searching: '{query}'")

        try:
            results = self._search_duckduckgo(query)
        except Exception as e:
            logger.warning(f"[WebSearchSkill] DuckDuckGo failed ({e}), falling back to Chrome search.")
            return [
                {"action": "open_app", "target": "chrome"},
                {"action": "wait", "seconds": 1.0},
                {"action": "hotkey", "keys": ["ctrl", "t"]},
                {"action": "type_text", "text": f"https://duckduckgo.com/?q={query.replace(' ', '+')}", "enter": True},
                {"action": "speak", "text": f"Searching for {query}."},
            ]

        if results:
            summary = results[0]  # top result snippet
            return [
                {"action": "open_app", "target": "chrome"},
                {"action": "wait", "seconds": 1.0},
                {"action": "hotkey", "keys": ["ctrl", "t"]},
                {"action": "type_text", "text": f"https://duckduckgo.com/?q={query.replace(' ', '+')}", "enter": True},
                {"action": "speak", "text": f"Here's what I found: {summary}"},
            ]
        return [
            {"action": "speak", "text": f"I couldn't find results for {query}, sir."},
        ]

    @staticmethod
    def _search_duckduckgo(query: str) -> list[str]:
        """Return up to 3 short snippets from DuckDuckGo Instant Answer API."""
        import requests
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        }
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()

        snippets = []
        if data.get("AbstractText"):
            snippets.append(data["AbstractText"][:300])
        for r in data.get("RelatedTopics", [])[:3]:
            if isinstance(r, dict) and r.get("Text"):
                snippets.append(r["Text"][:200])
        return snippets
