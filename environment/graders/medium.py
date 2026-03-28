from .base import BaseGrader
from ..models import Action, ActionType


class MediumGrader(BaseGrader):
    """
    Grades the medium task: logic bug where >= should be >.
    Agent must identify silent wrong output without an error message.
    """

    def grade_action(self, action: Action, step_number: int) -> dict:
        score = 0.0
        breakdown = {}
        feedback_parts = []
        done = False

        if action.action_type == ActionType.DIAGNOSE:
            text = (action.diagnosis or "") + (action.reasoning or "")

            # Did agent recognize no exception was thrown (silent bug)?
            if self._contains_any(text, ["silent", "no error", "no exception", "wrong output", "wrong result", "logic"]):
                breakdown["identified_silent_bug"] = 0.2
                score += 0.2
                feedback_parts.append("Recognized this is a silent logic bug.")
            else:
                breakdown["identified_silent_bug"] = 0.0
                feedback_parts.append("Did not identify this as a silent bug.")

            # Did agent find the comparison operator issue?
            if self._contains_any(text, [">=", "greater than or equal", "tie", "last seen", "insertion order"]):
                breakdown["identified_comparison_bug"] = 0.35
                score += 0.35
                feedback_parts.append("Correctly identified the >= comparison as root cause.")
            else:
                breakdown["identified_comparison_bug"] = 0.0
                feedback_parts.append("Did not identify the >= comparison issue.")

            # Did agent trace through a specific failing example?
            if self._contains_any(text, ["[4, 4, 7, 7]", "4,4,7,7", "tie-breaking", "first seen"]):
                breakdown["traced_example"] = 0.1
                score += 0.1
                feedback_parts.append("Traced through specific failing example.")

        elif action.action_type == ActionType.SUGGEST_FIX:
            fix = action.suggested_fix or ""
            if "> max_count" in fix and ">= max_count" not in fix:
                breakdown["correct_operator"] = 0.3
                score += 0.3
                feedback_parts.append("Suggested fix uses correct strict > operator.")
            else:
                breakdown["correct_operator"] = 0.0
                feedback_parts.append("Fix still uses >= or incorrect operator.")

        elif action.action_type == ActionType.SUBMIT_SOLUTION:
            result = self.grade_final_solution(action.final_solution or "")
            score = result["score"]
            breakdown = result["breakdown"]
            feedback_parts = [result["feedback"]]
            done = result["score"] >= 0.9

        elif action.action_type == ActionType.REQUEST_MORE_INFO:
            # Slight positive signal — agent is being thorough
            breakdown["asked_for_context"] = 0.05
            score += 0.05
            feedback_parts.append("Requested more info — reasonable for a silent bug.")

        # Step penalty
        if step_number > 5:
            penalty = min(0.1 * (step_number - 5), 0.2)
            score = max(0.0, score - penalty)
            breakdown["step_penalty"] = -penalty

        return {
            "score": round(min(score, 1.0), 3),
            "breakdown": breakdown,
            "feedback": " ".join(feedback_parts) or "No feedback.",
            "done": done
        }

    def grade_final_solution(self, solution_code: str) -> dict:
        score = 0.0
        breakdown = {}

        # Check fix is conceptually present
        if "> max_count" in solution_code and ">= max_count" not in solution_code:
            breakdown["operator_fixed"] = 0.4
            score += 0.4
        else:
            breakdown["operator_fixed"] = 0.0

        # Run test cases
        try:
            namespace = {}
            exec(solution_code, namespace)
            fn = namespace.get("find_most_frequent")
            if fn:
                test_cases = [
                    ([4, 4, 7, 7], 4),
                    ([1, 2, 2, 3, 3, 3, 1, 1, 1], 1),
                    ([5, 5, 3, 3, 3], 3),
                    ([9], 9),
                    ([2, 2, 2, 1, 1, 1], 2),
                ]
                passed = sum(1 for args, exp in test_cases if fn(args) == exp)
                test_score = (passed / len(test_cases)) * 0.6
                breakdown["test_cases_passed"] = f"{passed}/{len(test_cases)}"
                score += test_score
            else:
                breakdown["function_not_found"] = True
        except Exception as e:
            breakdown["execution_error"] = str(e)

        return {
            "score": round(min(score, 1.0), 3),
            "breakdown": breakdown,
            "feedback": (
                "All test cases pass. Logic bug correctly fixed." if score >= 0.9
                else f"Partial fix. Score: {score:.2f}. Check tie-breaking logic."
            )
        }
