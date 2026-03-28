MEDIUM_SCENARIO = {
    "task_id": "debug_medium_001",
    "difficulty": "medium",
    "description": "A function runs without crashing but produces wrong results. No error message is given. Diagnose and fix the logic bug.",
    "code_snippet": """\
def find_most_frequent(nums):
    \"\"\"Return the most frequently occurring number in the list.\"\"\"
    counts = {}
    for num in nums:
        if num in counts:
            counts[num] += 1
        else:
            counts[num] = 1

    max_count = 0
    result = None
    for num, count in counts.items():
        if count > max_count:
            max_count = count
            result = num

    return result

# Outputs wrong answer
print(find_most_frequent([1, 2, 2, 3, 3, 3, 1, 1, 1]))  # Should print 1
print(find_most_frequent([5, 5, 3, 3, 3]))                # Should print 3
""",
    "error_message": None,
    "stack_trace": None,
    "language": "python",
    "context": """\
The function should return the number that appears most frequently.
When run, it returns 3 for both cases instead of the correct answers (1 and 3).
No exception is raised — the code runs silently but produces wrong output.
""",
    "actual_output": {
        "[1, 2, 2, 3, 3, 3, 1, 1, 1]": 3,
        "[5, 5, 3, 3, 3]": 3
    },
    "expected_output": {
        "[1, 2, 2, 3, 3, 3, 1, 1, 1]": 1,
        "[5, 5, 3, 3, 3]": 3
    },
    "correct_bug_type": "logic",
    "correct_bug_description": "The comparison `count > max_count` uses strict greater-than. When iterating a dict in insertion order, the last key with the same max count wins — not the first. The fix is to track correctly or use >= with proper tie-breaking. Actually root cause: dict insertion order in Python 3.7+ means iteration goes in order items were added. The count for 3 is 3, same as 1 which is also 3 — but 1 is added first. Actually both have count 3 for [1,2,2,3,3,3,1,1,1]. The bug is > should handle ties by preferring first seen. Fix: change to >= with first-seen check or track properly.",
    "correct_fix": """\
def find_most_frequent(nums):
    counts = {}
    for num in nums:
        counts[num] = counts.get(num, 0) + 1

    max_count = 0
    result = None
    for num, count in counts.items():
        if count > max_count:
            max_count = count
            result = num
    return result
""",
    "note": "The actual bug is the counter logic doesn't handle the case where [1,2,2,3,3,3,1,1,1] → 1 appears 4 times not 3. The code IS correct — 1 appears 4 times (indices 0,6,7,8) so result should be 1. The bug is counts[num] = 1 when first seen instead of incrementing. Wait — the code does increment. Let me recount: 1 appears at positions 0,6,7,8 = 4 times. 3 appears at 3,4,5 = 3 times. So correct answer IS 1. The code should work... The actual intentional bug introduced: the else branch sets counts[num] = 1 but there's an off-by-one — when num is seen for the FIRST time it should be 1, which it is. The code is actually correct for this input. To make it buggy, we need to change it.",
    "max_steps": 8,
    "scoring_criteria": [
        "Identifies this is a logic bug (no exception)",
        "Correctly traces through the counting logic",
        "Identifies the off-by-one or comparison issue",
        "Provides a fix that passes all test cases"
    ]
}

MEDIUM_SCENARIO["code_snippet"] = """\
def find_most_frequent(nums):
    \"\"\"Return the most frequently occurring number in the list.\"\"\"
    counts = {}
    for num in nums:
        if num not in counts:
            counts[num] = 0
        counts[num] += 1

    max_count = 0
    result = None
    for num, count in counts.items():
        if count >= max_count:
            max_count = count
            result = num

    return result

# Outputs wrong answer — returns last tied element instead of first
print(find_most_frequent([1, 2, 2, 3, 3, 3, 1, 1, 1]))  # Expected: 1, Got: 1 (happens to work)
print(find_most_frequent([5, 5, 3, 3, 3]))                # Expected: 3, Got: 3 (happens to work)
print(find_most_frequent([4, 4, 7, 7]))                   # Expected: 4, Got: 7 (WRONG)
"""

MEDIUM_SCENARIO["context"] = """\
The function should return the FIRST number to reach the highest frequency.
For a tie, the number that appeared earliest in the list should win.
Input [4, 4, 7, 7] should return 4 (first to reach count=2), but returns 7.
No exception is raised.
"""

MEDIUM_SCENARIO["correct_bug_type"] = "logic"
MEDIUM_SCENARIO["correct_bug_description"] = "Using >= instead of > means ties go to the last-seen element, not first-seen."
MEDIUM_SCENARIO["correct_fix"] = """\
    for num, count in counts.items():
        if count > max_count:   # strict > preserves first-seen winner
            max_count = count
            result = num
"""

MEDIUM_TEST_CASES = [
    {"args": [[4, 4, 7, 7]], "expected": 4},
    {"args": [[1, 2, 2, 3, 3, 3, 1, 1, 1]], "expected": 1},
    {"args": [[5, 5, 3, 3, 3]], "expected": 3},
    {"args": [[9]], "expected": 9},
    {"args": [[2, 2, 2, 1, 1, 1]], "expected": 2},
]
