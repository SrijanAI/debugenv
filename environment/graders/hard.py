from .base import BaseGrader
from ..models import Action, ActionType


class HardGrader(BaseGrader):
    """
    Grades the hard task: 3 interacting bugs in an e-commerce cart system.
    
    Bug 1: Mutable default argument (cart=[])
    Bug 2: Integer division truncates tax (// instead of /)
    Bug 3: Off-by-one boundary condition (> instead of >=)
    
    Partial credit per bug found/fixed. Full score only when all 3 fixed
    AND all boundary test cases pass. Designed to resist frontier models —
    no hints in context, bugs interact, non-deterministic failure pattern.
    """

    def grade_action(self, action: Action, step_number: int) -> dict:
        score = 0.0
        breakdown = {}
        feedback_parts = []
        done = False

        text = (
            (action.diagnosis or "") +
            (action.reasoning or "") +
            (action.suggested_fix or "") +
            (action.final_solution or "")
        ).lower()

        if action.action_type == ActionType.DIAGNOSE:

            # Bug 1: mutable default argument
            if self._contains_any(text, [
                "mutable default", "default argument", "cart=[]", "cart=none",
                "shared state", "persists between", "evaluated once",
                "default mutable", "list as default"
            ]):
                breakdown["found_bug1_mutable_default"] = 0.2
                score += 0.2
                feedback_parts.append("Found Bug 1: mutable default argument.")
            else:
                breakdown["found_bug1_mutable_default"] = 0.0

            # Bug 2: integer division
            if self._contains_any(text, [
                "integer division", "floor division", "//", "truncat",
                "loses cents", "precision", "tax calculation", "int division"
            ]):
                breakdown["found_bug2_integer_division"] = 0.15
                score += 0.15
                feedback_parts.append("Found Bug 2: integer division truncates tax.")
            else:
                breakdown["found_bug2_integer_division"] = 0.0

            # Bug 3: boundary condition
            if self._contains_any(text, [
                "boundary", "off-by-one", ">= 100", ">= 500",
                "exactly 100", "exactly 500", "boundary condition",
                "greater than or equal", "edge case", "border"
            ]):
                breakdown["found_bug3_boundary"] = 0.15
                score += 0.15
                feedback_parts.append("Found Bug 3: off-by-one boundary condition.")
            else:
                breakdown["found_bug3_boundary"] = 0.0

            # Bonus: agent identifies non-determinism / call-order issue
            if self._contains_any(text, [
                "non-deterministic", "call order", "test order",
                "depends on", "previous call", "stateful"
            ]):
                breakdown["identified_nondeterminism"] = 0.05
                score += 0.05
                feedback_parts.append("Identified non-deterministic behavior.")

            if not feedback_parts:
                feedback_parts.append("No bugs correctly identified. Look for Python-specific gotchas.")

        elif action.action_type == ActionType.SUGGEST_FIX:
            fix = (action.suggested_fix or "").lower()

            if self._contains_any(fix, ["cart=none", "if cart is none", "cart = none", "none"]):
                breakdown["fix1_suggested"] = 0.1
                score += 0.1
                feedback_parts.append("Suggested mutable default fix.")

            if "/" in fix and "//" not in fix and "tax" in fix:
                breakdown["fix2_suggested"] = 0.1
                score += 0.1
                feedback_parts.append("Suggested integer division fix.")

            if self._contains_any(fix, [">= 100", ">= 500", ">=100", ">=500"]):
                breakdown["fix3_suggested"] = 0.1
                score += 0.1
                feedback_parts.append("Suggested boundary condition fix.")

        elif action.action_type == ActionType.SUBMIT_SOLUTION:
            result = self.grade_final_solution(action.final_solution or "")
            score = result["score"]
            breakdown = result["breakdown"]
            feedback_parts = [result["feedback"]]
            done = result["score"] >= 0.85

        elif action.action_type == ActionType.REQUEST_MORE_INFO:
            breakdown["asked_for_info"] = 0.03
            score += 0.03
            feedback_parts.append("Requested more context — reasonable for a silent multi-bug scenario.")

        # Penalty only after step 9
        if step_number > 9:
            penalty = min(0.05 * (step_number - 9), 0.15)
            score = max(0.0, score - penalty)
            breakdown["step_penalty"] = round(-penalty, 3)

        if not feedback_parts:
            feedback_parts.append("No clear signal from this action.")

        return {
            "score": round(min(score, 1.0), 3),
            "breakdown": breakdown,
            "feedback": " ".join(feedback_parts),
            "done": done
        }

    def grade_final_solution(self, solution_code: str) -> dict:
        score = 0.0
        breakdown = {}
        bugs_fixed = 0

        # --- Static checks ---

        # Bug 1 fix: cart=None + if cart is None
        has_none_default = "cart=None" in solution_code or "cart = None" in solution_code
        has_none_check = "if cart is None" in solution_code or "if cart is none" in solution_code.lower()
        if has_none_default and has_none_check:
            breakdown["fix1_mutable_default"] = 0.2
            score += 0.2
            bugs_fixed += 1
        else:
            breakdown["fix1_mutable_default"] = 0.0

        # Bug 2 fix: / instead of // for tax
        # Look for tax line with regular division
        import re
        tax_lines = [l for l in solution_code.splitlines() if "tax" in l.lower() and "100" in l]
        bug2_fixed = any("/" in l and "//" not in l for l in tax_lines)
        if bug2_fixed:
            breakdown["fix2_integer_division"] = 0.2
            score += 0.2
            bugs_fixed += 1
        else:
            breakdown["fix2_integer_division"] = 0.0

        # Bug 3 fix: >= boundaries
        has_gte_100 = ">= 100" in solution_code or ">=100" in solution_code
        has_gte_500 = ">= 500" in solution_code or ">=500" in solution_code
        if has_gte_100 and has_gte_500:
            breakdown["fix3_boundary_condition"] = 0.2
            score += 0.2
            bugs_fixed += 1
        else:
            breakdown["fix3_boundary_condition"] = 0.0

        breakdown["bugs_fixed_statically"] = f"{bugs_fixed}/3"

        # --- Dynamic execution tests ---
        try:
            namespace = {}
            exec(solution_code, namespace)

            add_fn = namespace.get("add_to_cart")
            discount_fn = namespace.get("apply_discount")
            total_fn = namespace.get("calculate_total")

            if add_fn and discount_fn and total_fn:
                test_results = {}

                # Test 1: mutable default isolation
                c1 = add_fn("Item A", 10.0, 1)
                c2 = add_fn("Item B", 20.0, 1)  # Should NOT contain Item A
                test_results["isolation"] = len(c2) == 1
                if test_results["isolation"]:
                    breakdown["test_isolation"] = 0.1
                    score += 0.1
                else:
                    breakdown["test_isolation"] = 0.0

                # Test 2: tax precision (8% on 100.00 should be 8.0 not 8)
                cart_t = add_fn("X", 100.0, 1)
                total_t = total_fn(cart_t, "standard", 8)
                expected_t = round(100.0 + 100.0 * 8 / 100, 2)
                test_results["tax_precision"] = abs(total_t - expected_t) < 0.01
                if test_results["tax_precision"]:
                    breakdown["test_tax_precision"] = 0.1
                    score += 0.1
                else:
                    breakdown["test_tax_precision"] = 0.0
                    breakdown["tax_expected"] = expected_t
                    breakdown["tax_got"] = total_t

                # Test 3: boundary — premium at exactly 100
                result_boundary_premium = discount_fn(100.0, "premium")
                test_results["boundary_premium"] = abs(result_boundary_premium - 90.0) < 0.01
                if test_results["boundary_premium"]:
                    breakdown["test_boundary_premium_100"] = 0.1
                    score += 0.1
                else:
                    breakdown["test_boundary_premium_100"] = 0.0
                    breakdown["boundary_premium_expected"] = 90.0
                    breakdown["boundary_premium_got"] = result_boundary_premium

                # Test 4: boundary — vip at exactly 500
                result_boundary_vip = discount_fn(500.0, "vip")
                test_results["boundary_vip"] = abs(result_boundary_vip - 400.0) < 0.01
                if test_results["boundary_vip"]:
                    breakdown["test_boundary_vip_500"] = 0.1
                    score += 0.1
                else:
                    breakdown["test_boundary_vip_500"] = 0.0
                    breakdown["boundary_vip_expected"] = 400.0
                    breakdown["boundary_vip_got"] = result_boundary_vip

                breakdown["dynamic_tests"] = test_results
                passed = sum(1 for v in test_results.values() if v)
                breakdown["dynamic_tests_passed"] = f"{passed}/{len(test_results)}"

            else:
                breakdown["functions_not_found"] = True

        except Exception as e:
            breakdown["execution_error"] = str(e)

        final_score = round(min(score, 1.0), 3)
        all_pass = bugs_fixed == 3 and breakdown.get("dynamic_tests_passed") == "4/4"

        return {
            "score": final_score,
            "breakdown": breakdown,
            "feedback": (
                "All 3 bugs fixed. All boundary tests pass." if all_pass
                else f"Partial fix. {bugs_fixed}/3 bugs fixed statically. Score: {final_score:.2f}. "
                     f"Check: mutable default, integer division, boundary conditions."
            )
        }
