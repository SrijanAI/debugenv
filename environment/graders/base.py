from abc import ABC, abstractmethod
from typing import Optional
from ..models import Action, ActionType


class BaseGrader(ABC):
    """Base class for all task graders. Graders are deterministic — same inputs always produce same score."""

    def __init__(self, scenario: dict):
        self.scenario = scenario

    @abstractmethod
    def grade_action(self, action: Action, step_number: int) -> dict:
        """
        Grade a single action. Returns a dict with:
        - score: float 0.0-1.0
        - feedback: str
        - breakdown: dict of partial scores
        - done: bool
        """
        pass

    @abstractmethod
    def grade_final_solution(self, solution_code: str) -> dict:
        """Grade the final submitted solution. Deterministic pass/fail + partial."""
        pass

    def _normalize(self, text: str) -> str:
        return text.lower().strip() if text else ""

    def _contains_any(self, text: str, keywords: list) -> bool:
        t = self._normalize(text)
        return any(k.lower() in t for k in keywords)
