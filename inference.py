"""
Baseline inference script for DebugEnv.
Uses the OpenAI API client to run an LLM agent against all 3 tasks.
Reads OPENAI_API_KEY from environment variables.
Produces reproducible baseline scores.

Usage:
    export OPENAI_API_KEY=your_key_here
    python baseline/inference.py
"""

import os
import json
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from environment import DebugEnv, Action, ActionType

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an expert software debugger. You will be shown buggy code and must:
1. Diagnose the bug
2. Suggest a fix
3. Submit the corrected solution

Always respond in valid JSON matching the action schema exactly.

Action schema:
{
  "action_type": one of ["diagnose", "suggest_fix", "request_more_info", "submit_solution"],
  "diagnosis": "your diagnosis (for diagnose action)",
  "suggested_fix": "fixed code snippet (for suggest_fix action)",
  "question": "clarifying question (for request_more_info action)",
  "final_solution": "complete corrected code (for submit_solution action)",
  "reasoning": "your reasoning"
}

Be concise and precise. Focus on root causes, not symptoms."""


def build_user_message(obs) -> str:
    parts = [
        f"Task: {obs.task_id} (Difficulty: {obs.difficulty})",
        f"\nCode:\n```python\n{obs.code_snippet}\n```"
    ]
    if obs.error_message:
        parts.append(f"\nError: {obs.error_message}")
    if obs.stack_trace:
        parts.append(f"\nStack trace:\n{obs.stack_trace}")
    if obs.context:
        parts.append(f"\nContext: {obs.context}")
    if obs.previous_attempts:
        parts.append(f"\nPrevious feedback: {obs.previous_attempts[-1]}")
    parts.append(f"\nStep {obs.step_number + 1}/{obs.max_steps}. What is your action?")
    return "\n".join(parts)


def parse_action(response_text: str) -> Action:
    """Parse LLM response into Action object."""
    text = response_text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])
    data = json.loads(text)
    return Action(**data)


def run_agent_on_task(task_id: str, max_steps: int = 5, model: str = "gpt-4o-mini") -> dict:
    """Run LLM agent on a single task. Returns score and episode info."""
    env = DebugEnv(task_id=task_id)
    obs = env.reset()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    episode_log = []
    final_score = 0.0
    done = False

    print(f"\n{'='*50}")
    print(f"Task: {task_id.upper()}")
    print(f"{'='*50}")

    for step in range(max_steps):
        if done:
            break

        user_msg = build_user_message(obs)
        messages.append({"role": "user", "content": user_msg})

        # Call LLM
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,  # Low temp for reproducibility
            response_format={"type": "json_object"}
        )

        raw = response.choices[0].message.content
        messages.append({"role": "assistant", "content": raw})

        print(f"\nStep {step + 1}: {raw[:200]}...")

        try:
            action = parse_action(raw)
        except Exception as e:
            print(f"  Parse error: {e}")
            action = Action(
                action_type=ActionType.DIAGNOSE,
                diagnosis="Unable to parse previous response",
                reasoning="Fallback action"
            )

        result = env.step(action)
        obs = result.observation
        final_score = result.reward.value
        done = result.done

        episode_log.append({
            "step": step + 1,
            "action_type": action.action_type.value,
            "score": final_score,
            "feedback": result.reward.feedback
        })

        print(f"  Score: {final_score:.3f} | {result.reward.feedback}")

        # If agent chose to submit, we're done
        if action.action_type == ActionType.SUBMIT_SOLUTION or done:
            break

    # If agent hasn't submitted yet, force a submission
    if not done:
        print(f"\nForcing submission after {max_steps} steps...")
        messages.append({
            "role": "user",
            "content": "Time is up. Submit your final solution now using submit_solution action."
        })
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        raw = response.choices[0].message.content
        try:
            action = parse_action(raw)
            if action.action_type != ActionType.SUBMIT_SOLUTION:
                action = Action(
                    action_type=ActionType.SUBMIT_SOLUTION,
                    final_solution=action.final_solution or obs.code_snippet,
                    reasoning="Forced submission"
                )
        except Exception:
            action = Action(
                action_type=ActionType.SUBMIT_SOLUTION,
                final_solution=obs.code_snippet,
                reasoning="Forced fallback submission"
            )
        result = env.step(action)
        final_score = result.reward.value
        print(f"  Final score: {final_score:.3f}")

    print(f"\nFinal score for {task_id}: {final_score:.3f}")
    return {
        "task_id": task_id,
        "score": final_score,
        "steps": len(episode_log),
        "episode_log": episode_log
    }


def run_baseline(model: str = "gpt-4o-mini") -> dict:
    """Run baseline agent on all 3 tasks. Returns reproducible scores."""
    print(f"Running DebugEnv baseline with model: {model}")
    print(f"API key: {'set' if os.environ.get('OPENAI_API_KEY') else 'NOT SET'}")

    results = {}
    for task_id in ["easy", "medium", "hard"]:
        result = run_agent_on_task(task_id, model=model)
        results[task_id] = result

    print(f"\n{'='*50}")
    print("BASELINE RESULTS")
    print(f"{'='*50}")
    for tid, r in results.items():
        print(f"  {tid.upper():8s}: {r['score']:.3f}")
    avg = sum(r["score"] for r in results.values()) / len(results)
    print(f"  {'AVERAGE':8s}: {avg:.3f}")
    print(f"{'='*50}")

    return {
        "model": model,
        "scores": {tid: r["score"] for tid, r in results.items()},
        "average": avg,
        "details": results
    }


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "gpt-4o-mini"
    results = run_baseline(model=model)
    with open("baseline_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to baseline_results.json")
