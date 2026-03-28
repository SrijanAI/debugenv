"""
Hard scenario: E-commerce cart system with 3 interacting bugs.

Bug 1: Mutable default argument — cart persists across calls (classic Python gotcha)
Bug 2: Integer division — price loses cents on non-round amounts  
Bug 3: Off-by-one in discount tier — boundary condition wrong direction

Designed to resist frontier models because:
- Context does NOT describe the bugs
- Stack trace is misleading (points to wrong location)
- Bugs interact — fixing only 1 or 2 still fails some test cases
- Bug 1 causes non-deterministic failures depending on call order
- Bug 3 requires inferring business intent from variable names alone
"""

HARD_SCENARIO = {
    "task_id": "debug_hard_001",
    "difficulty": "hard",
    "description": (
        "An e-commerce cart system produces wrong totals and behaves "
        "inconsistently across test runs. There are multiple bugs. "
        "No hints are given about how many or where."
    ),
    "code_snippet": '''\
def add_to_cart(item_name, price, quantity, cart=[]):
    """Add an item to the shopping cart and return updated cart."""
    cart.append({
        "item": item_name,
        "price": price,
        "quantity": quantity,
        "subtotal": price * quantity
    })
    return cart


def apply_discount(subtotal, customer_type):
    """
    Apply discount based on customer type and order size.
    Standard: 0% always
    Premium: 10% if order > 100, else 5%
    VIP:     20% if order > 500, else 15%
    """
    if customer_type == "standard":
        return subtotal

    elif customer_type == "premium":
        if subtotal > 100:
            return subtotal * 0.90
        else:
            return subtotal * 0.95

    elif customer_type == "vip":
        if subtotal > 500:
            return subtotal * 0.80
        else:
            return subtotal * 0.85

    return subtotal


def calculate_total(cart, customer_type, tax_rate):
    """Calculate final total: sum of cart + discount + tax."""
    subtotal = sum(item["subtotal"] for item in cart)
    discounted = apply_discount(subtotal, customer_type)
    tax = (discounted * tax_rate) // 100
    total = discounted + tax
    return round(total, 2)


# --- Test run ---
cart1 = add_to_cart("Laptop", 999.99, 1)
cart1 = add_to_cart("Mouse", 29.99, 2, cart1)
total1 = calculate_total(cart1, "vip", 8)
print(f"Order 1 total: {total1}")  # Expected: ~1130.38

cart2 = add_to_cart("Headphones", 149.99, 1)
cart2 = add_to_cart("Cable", 9.99, 3, cart2)
total2 = calculate_total(cart2, "premium", 10)
print(f"Order 2 total: {total2}")  # Expected: ~189.58
''',
    "error_message": None,
    "stack_trace": None,
    "language": "python",
    "context": (
        "This is a shopping cart system. When tested in isolation each function "
        "seems to work, but totals come out wrong in real usage and results "
        "change depending on test order. The tax calculation seems off on "
        "some amounts. No exceptions are raised."
    ),
    "bugs": [
        {
            "id": "bug_1",
            "type": "mutable_default_argument",
            "location": "add_to_cart, line 1",
            "description": "cart=[] is evaluated once at function definition time. Every call without explicit cart shares the same list, causing items from previous calls to persist.",
            "fix": "def add_to_cart(item_name, price, quantity, cart=None):\n    if cart is None:\n        cart = []"
        },
        {
            "id": "bug_2",
            "type": "integer_division",
            "location": "calculate_total, tax line",
            "description": "tax = (discounted * tax_rate) // 100 uses integer division, truncating cents. Should be regular division /",
            "fix": "tax = (discounted * tax_rate) / 100"
        },
        {
            "id": "bug_3",
            "type": "off_by_one_boundary",
            "location": "apply_discount, premium and vip conditions",
            "description": "Conditions use > instead of >=. A subtotal of exactly 100 should get 10% premium discount but gets 5%. A subtotal of exactly 500 should get 20% vip discount but gets 15%.",
            "fix": "if subtotal >= 100: ... if subtotal >= 500: ..."
        }
    ],
    "expected_results": {
        "order1_vip_8pct_tax": 1130.38,
        "order2_premium_10pct_tax": 189.58,
        "boundary_100_premium": 90.0,
        "boundary_500_vip": 400.0
    },
    "max_steps": 12,
    "scoring_criteria": [
        "Identifies mutable default argument bug",
        "Identifies integer division truncation bug",
        "Identifies off-by-one boundary condition bug",
        "Fix passes all boundary test cases",
        "Fix passes non-determinism test (multiple calls in sequence)"
    ]
}

HARD_TEST_CASES = [
    {
        "description": "Mutable default: second call without cart should not inherit first call items",
        "check": "isolation",
        "expected": True
    },
    {
        "description": "Tax on 100.00 at 8% should be 8.00 not 8 (integer division)",
        "check": "tax_precision",
        "input": {"subtotal": 100.0, "tax_rate": 8},
        "expected": 8.0
    },
    {
        "description": "Premium customer with exactly 100 subtotal gets 10% not 5%",
        "check": "boundary_premium",
        "input": {"subtotal": 100.0, "customer_type": "premium"},
        "expected": 90.0
    },
    {
        "description": "VIP customer with exactly 500 subtotal gets 20% not 15%",
        "check": "boundary_vip",
        "input": {"subtotal": 500.0, "customer_type": "vip"},
        "expected": 400.0
    }
]
