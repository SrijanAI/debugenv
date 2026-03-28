from .base import BaseGrader
from ..models import Action, ActionType


class EasyGrader(BaseGrader):
    """
    Grades the easy task: NameError from typo 'discont_percent' vs 'discount_percent'.
    All scoring is deterministic based on content matching.
    """

    def grade_action(self, action: Action, step_number: int) -> dict:
        score = 0.0
        breakdown = {}
        feedback_parts = []
        done = False

        if action.action_type == ActionType.DIAGNOSE:
            text = (action.diagnosis or "") + (action.reasoning or "")

            # Did agent identify it's a NameError?
            if self._contains_any(text, ["NameError", "name error", "not defined"]):
                breakdown["identified_error_type"] = 0.2
                score += 0.2
                feedback_parts.append("Correctly identified the NameError.")
            else:
                breakdown["identified_error_type"] = 0.0
                feedback_parts.append("Did not correctly identify error type.")

            # Did agent find the typo?
            if self._contains_any(text, ["typo", "misspell", "discont_percent", "spelling"]):
                breakdown["identified_typo"] = 0.3
                score += 0.3
                feedback_parts.append("Found the typo 'discont_percent'.")
            else:
                breakdown["identified_typo"] = 0.0
                feedback_parts.append("Did not identify the typo as root cause.")

        elif action.action_type == ActionType.SUGGEST_FIX:
            fix = action.suggested_fix or ""
            if "discount_percent" in fix and "discont_percent" not in fix:
                breakdown["correct_variable_name"] = 0.3
                score += 0.3
                feedback_parts.append("Suggested fix uses correct variable name.")
            else:
                breakdown["correct_variable_name"] = 0.0
                feedback_parts.append("Fix still contains incorrect variable name.")

        elif action.action_type == ActionType.SUBMIT_SOLUTION:
            result = self.grade_final_solution(action.final_solution or "")
            score = result["score"]
            breakdown = result["breakdown"]
            feedback_parts = [result["feedback"]]
            done = result["score"] >= 0.9

        # Penalize excessive steps
        if step_number > 3:
            penalty = min(0.1 * (step_number - 3), 0.2)
            score = max(0.0, score - penalty)
            breakdown["step_penalty"] = -penalty
            feedback_parts.append(f"Step penalty applied (-{penalty:.1f}) for using {step_number} steps.")

        return {
            "score": round(min(score, 1.0), 3),
            "breakdown": breakdown,
            "feedback": " ".join(feedback_parts) or "No feedback.",
            "done": done
        }

    def grade_final_solution(self, solution_code: str) -> dict:
        score = 0.0
        breakdown = {}

        # Check fix is present
        if "discount_percent" in solution_code and "discont_percent" not in solution_code:
            breakdown["typo_fixed"] = 0.5
            score += 0.5
        else:
            breakdown["typo_fixed"] = 0.0

        # Run test cases
        try:
            namespace = {}
            exec(solution_code, namespace)
            fn = namespace.get("calculate_discount")
            if fn:
                test_cases = [
                    (100, 20, 80.0),
                    (200, 50, 100.0),
                    (150, 10, 135.0),
                    (0, 20, 0.0),
                ]
                passed = sum(1 for price, disc, exp in test_cases if abs(fn(price, disc) - exp) < 0.01)
                test_score = (passed / len(test_cases)) * 0.5
                breakdown["test_cases_passed"] = f"{passed}/{len(test_cases)}"
                breakdown["test_score"] = test_score
                score += test_score
            else:
                breakdown["function_not_found"] = True
        except Exception as e:
            breakdown["execution_error"] = str(e)

        return {
            "score": round(min(score, 1.0), 3),
            "breakdown": breakdown,
            "feedback": (
                "Solution correct and all tests pass." if score >= 0.9
                else f"Partial solution. Score: {score:.2f}"
            )
        }
