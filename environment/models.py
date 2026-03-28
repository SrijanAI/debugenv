from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from enum import Enum


class ActionType(str, Enum):
    DIAGNOSE = "diagnose"
    SUGGEST_FIX = "suggest_fix"
    REQUEST_MORE_INFO = "request_more_info"
    SUBMIT_SOLUTION = "submit_solution"


class Observation(BaseModel):
    task_id: str = Field(..., description="Unique task identifier")
    difficulty: Literal["easy", "medium", "hard"]
    code_snippet: str = Field(..., description="The buggy code")
    error_message: Optional[str] = Field(None, description="Runtime error or exception message")
    stack_trace: Optional[str] = Field(None, description="Full stack trace if available")
    language: str = Field(default="python", description="Programming language")
    context: Optional[str] = Field(None, description="Additional context about what the code should do")
    available_actions: List[ActionType] = Field(
        default_factory=lambda: list(ActionType),
        description="Actions the agent can take in this step"
    )
    step_number: int = Field(default=0, description="Current step in the episode")
    max_steps: int = Field(default=10, description="Maximum steps allowed")
    previous_attempts: List[str] = Field(
        default_factory=list,
        description="List of previous action summaries in this episode"
    )


class Action(BaseModel):
    action_type: ActionType = Field(..., description="Type of action to take")
    diagnosis: Optional[str] = Field(
        None,
        description="Agent's diagnosis of the bug — required for DIAGNOSE action"
    )
    suggested_fix: Optional[str] = Field(
        None,
        description="Code fix suggestion — required for SUGGEST_FIX action"
    )
    question: Optional[str] = Field(
        None,
        description="Clarifying question — required for REQUEST_MORE_INFO action"
    )
    final_solution: Optional[str] = Field(
        None,
        description="Final corrected code — required for SUBMIT_SOLUTION action"
    )
    reasoning: Optional[str] = Field(
        None,
        description="Agent's reasoning for this action"
    )


class Reward(BaseModel):
    value: float = Field(..., ge=0.0, le=1.0, description="Reward value between 0.0 and 1.0")
    breakdown: dict = Field(
        default_factory=dict,
        description="Partial reward components explaining the score"
    )
    feedback: str = Field(..., description="Human-readable feedback on the action")
    done: bool = Field(default=False, description="Whether the episode is complete")


class StepResult(BaseModel):
    observation: Observation
    reward: Reward
    done: bool
    info: dict = Field(default_factory=dict)


class TaskInfo(BaseModel):
    task_id: str
    difficulty: Literal["easy", "medium", "hard"]
    description: str
    action_schema: dict
    max_steps: int
    scoring_criteria: List[str]
