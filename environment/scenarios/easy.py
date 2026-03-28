EASY_SCENARIO = {
    "task_id": "debug_easy_001",
    "difficulty": "easy",
    "description": "A simple Python function crashes at runtime with a clear error message. Identify the bug and fix it.",
    "code_snippet": """\
def calculate_discount(price, discount_percent):
    \"\"\"Calculate the discounted price.\"\"\"
    discount_amount = price * (discont_percent / 100)
    final_price = price - discount_amount
    return final_price

# Test
result = calculate_discount(100, 20)
print(f"Discounted price: {result}")
""",
    "error_message": "NameError: name 'discont_percent' is not defined",
    "stack_trace": """\
Traceback (most recent call last):
  File "store.py", line 8, in <module>
    result = calculate_discount(100, 20)
  File "store.py", line 3, in calculate_discount
    discount_amount = price * (discont_percent / 100)
NameError: name 'discont_percent' is not defined
""",
    "language": "python",
    "context": "This function should apply a percentage discount to a price and return the final price.",
    "correct_bug_type": "typo",
    "correct_bug_location": "line 3",
    "correct_variable": "discount_percent",
    "typo_variable": "discont_percent",
    "correct_fix": "discount_amount = price * (discount_percent / 100)",
    "max_steps": 5,
    "scoring_criteria": [
        "Correctly identifies the NameError",
        "Identifies the typo as root cause",
        "Provides correct fix with right variable name",
        "Solution passes all test cases"
    ]
}

EASY_TEST_CASES = [
    {"args": [100, 20], "expected": 80.0},
    {"args": [200, 50], "expected": 100.0},
    {"args": [150, 10], "expected": 135.0},
    {"args": [0, 20], "expected": 0.0},
]
