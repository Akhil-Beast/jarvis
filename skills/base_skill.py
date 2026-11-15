"""
skills/base_skill.py — Abstract base class for all JARVIS skills.
"""
from abc import ABC, abstractmethod


class BaseSkill(ABC):
    """All JARVIS skills must inherit from this class."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable skill name."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """One-line description of what this skill does."""
        ...

    @abstractmethod
    def can_handle(self, command: str) -> bool:
        """Return True if this skill should handle the given command string."""
        ...

    @abstractmethod
    def execute(self, command: str, context: dict | None = None) -> list[dict]:
        """
        Execute the skill and return a list of action-step dicts compatible
        with the orchestrator.  Example:
            [{"action": "speak", "text": "Done."}]
        """
        ...
