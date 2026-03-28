from typing import Optional, Dict, Any
from .models import Observation, Action, Reward, StepResult, TaskInfo, ActionType
from .scenarios import SCENARIOS
from .graders import GRADERS
import copy


class DebugEnv:
    """
    DebugEnv — an OpenEnv-compliant environment for training AI agents to debug code.
    
    Simulates real-world debugging scenarios ranging from simple typos (easy)
    to multi-function logic cascades (hard). Provides partial rewards at each step.
    """

    def __init__(self, task_id: str = "easy"):
        valid = list(SCENARIOS.keys())
        if task_id not in valid:
            raise ValueError(f"task_id must be one of {valid}")
        self.task_id = task_id
        self._scenario = SCENARIOS[task_id]
        self._grader = GRADERS[task_id](self._scenario)
        self._step_number = 0
        self._done = False
        self._history = []
        self._cumulative_score = 0.0
        self._episode_info: Dict[str, Any] = {}

    def reset(self) -> Observation:
        """Reset environment to initial state. Returns initial observation."""
        self._step_number = 0
        self._done = False
        self._history = []
        self._cumulative_score = 0.0
        self._episode_info = {}
        return self._build_observation()

    def step(self, action: Action) -> StepResult:
        """
        Take one step in the environment.
        Returns: observation, reward, done, info
        """
        if self._done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")

        # Grade the action
        grade = self._grader.grade_action(action, self._step_number)

        # Build reward
        reward = Reward(
            value=grade["score"],
            breakdown=grade["breakdown"],
            feedback=grade["feedback"],
            done=grade["done"]
        )

        # Update state
        self._step_number += 1
        self._cumulative_score = max(self._cumulative_score, grade["score"])
        self._history.append({
            "step": self._step_number,
            "action_type": action.action_type.value,
            "score": grade["score"],
            "feedback": grade["feedback"]
        })

        # Episode ends if: agent submits solution, grader says done, or max steps hit
        if grade["done"] or action.action_type == ActionType.SUBMIT_SOLUTION:
            self._done = True
        elif self._step_number >= self._scenario["max_steps"]:
            self._done = True
            reward.feedback += " Maximum steps reached."

        self._episode_info = {
            "task_id": self.task_id,
            "steps_taken": self._step_number,
            "cumulative_score": self._cumulative_score,
            "history": self._history
        }

        next_obs = self._build_observation()
        return StepResult(
            observation=next_obs,
            reward=reward,
            done=self._done,
            info=self._episode_info
        )

    def state(self) -> Dict[str, Any]:
        """Return current internal state of the environment."""
        return {
            "task_id": self.task_id,
            "difficulty": self._scenario["difficulty"],
            "step_number": self._step_number,
            "done": self._done,
            "cumulative_score": self._cumulative_score,
            "max_steps": self._scenario["max_steps"],
            "history": copy.deepcopy(self._history)
        }

    def _build_observation(self) -> Observation:
        s = self._scenario
        return Observation(
            task_id=s["task_id"],
            difficulty=s["difficulty"],
            code_snippet=s["code_snippet"],
            error_message=s.get("error_message"),
            stack_trace=s.get("stack_trace"),
            language=s.get("language", "python"),
            context=s.get("context"),
            available_actions=list(ActionType),
            step_number=self._step_number,
            max_steps=s["max_steps"],
            previous_attempts=[h["feedback"] for h in self._history[-3:]]
        )

    def tasks(self):
        """Return list of available tasks with metadata."""
        return [
            TaskInfo(
                task_id=SCENARIOS[tid]["task_id"],
                difficulty=SCENARIOS[tid]["difficulty"],
                description=SCENARIOS[tid]["description"],
                action_schema=Action.model_json_schema(),
                max_steps=SCENARIOS[tid]["max_steps"],
                scoring_criteria=SCENARIOS[tid]["scoring_criteria"]
            )
            for tid in SCENARIOS
        ]
