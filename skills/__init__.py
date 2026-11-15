"""
skills/__init__.py — Skill Registry

Discovers and loads all BaseSkill subclasses from this package so brain.py
can delegate to them without knowing each skill's internal details.
"""
from importlib import import_module
from pathlib import Path
from core.safety import logger
from skills.base_skill import BaseSkill


class SkillRegistry:
    """Auto-discovers and indexes all skills in the skills/ directory."""

    def __init__(self):
        self._skills: list[BaseSkill] = []
        self._load_skills()

    def _load_skills(self):
        skills_dir = Path(__file__).parent
        for py_file in sorted(skills_dir.glob("*_skill.py")):
            module_name = f"skills.{py_file.stem}"
            try:
                mod = import_module(module_name)
                for attr_name in dir(mod):
                    obj = getattr(mod, attr_name)
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, BaseSkill)
                        and obj is not BaseSkill
                    ):
                        instance = obj()
                        self._skills.append(instance)
                        logger.info(f"[Skills] Loaded skill: {instance.name}")
            except Exception as e:
                logger.warning(f"[Skills] Failed to load {module_name}: {e}")

    def find_skill(self, command: str) -> BaseSkill | None:
        """Return the first skill that claims it can handle the command."""
        for skill in self._skills:
            try:
                if skill.can_handle(command):
                    return skill
            except Exception:
                continue
        return None

    @property
    def all_skills(self) -> list[BaseSkill]:
        return list(self._skills)


skill_registry = SkillRegistry()
