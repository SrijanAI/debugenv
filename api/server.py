from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from environment import DebugEnv, Action, ActionType

app = FastAPI(
    title="DebugEnv",
    description="OpenEnv-compliant environment for training AI agents to debug code.",
    version="1.0.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_sessions: Dict[str, DebugEnv] = {}

def _get_or_create(task_id: str) -> DebugEnv:
    if task_id not in _sessions:
        _sessions[task_id] = DebugEnv(task_id=task_id)
    return _sessions[task_id]

def _validate_task(task_id: str):
    if task_id not in ["easy", "medium", "hard"]:
        raise HTTPException(400, f"task_id must be one of ['easy', 'medium', 'hard']")

@app.get("/")
def root():
    return {
        "name": "DebugEnv",
        "description": "Train AI agents to debug real-world code errors.",
        "tasks": ["easy", "medium", "hard"],
        "endpoints": ["/reset", "/step", "/state", "/tasks", "/grader", "/baseline"]
    }

@app.post("/reset")
def reset(task_id: str = "easy"):
    _validate_task(task_id)
    env = DebugEnv(task_id=task_id)
    _sessions[task_id] = env
    obs = env.reset()
    return obs.model_dump()

@app.post("/step")
def step(action: Dict[str, Any], task_id: str = "easy"):
    _validate_task(task_id)
    env = _get_or_create(task_id)
    try:
        action_obj = Action(**action)
    except Exception as e:
        raise HTTPException(400, f"Invalid action: {e}")
    try:
        result = env.step(action_obj)
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    return {
        "observation": result.observation.model_dump(),
        "reward": result.reward.model_dump(),
        "done": result.done,
        "info": result.info
    }

@app.get("/state")
def state(task_id: str = "easy"):
    _validate_task(task_id)
    return _get_or_create(task_id).state()

@app.get("/tasks")
def tasks():
    return [t.model_dump() for t in DebugEnv(task_id="easy").tasks()]

@app.post("/grader")
def grader(task_id: str = "easy"):
    _validate_task(task_id)
    s = _get_or_create(task_id).state()
    return {
        "task_id": task_id,
        "steps_taken": s["step_number"],
        "cumulative_score": s["cumulative_score"],
        "done": s["done"],
        "history": s["history"]
    }

@app.post("/baseline")
def baseline():
    results = {}
    for task_id in ["easy", "medium", "hard"]:
        env = DebugEnv(task_id=task_id)
        obs = env.reset()

        if task_id == "easy":
            diagnosis = "NameError caused by typo 'discont_percent' instead of 'discount_percent'"
            solution = obs.code_snippet.replace("discont_percent", "discount_percent")
        elif task_id == "medium":
            diagnosis = "Silent logic bug: >= operator causes last tied element to win instead of first"
            solution = obs.code_snippet.replace(">= max_count", "> max_count")
        else:
            diagnosis = "Three bugs: mutable default argument cart=[], integer division // truncates tax, off-by-one boundary uses > instead of >="
            solution = """
def add_to_cart(item_name, price, quantity, cart=None):
    if cart is None:
        cart = []
    cart.append({"item": item_name, "price": price, "quantity": quantity, "subtotal": price * quantity})
    return cart

def apply_discount(subtotal, customer_type):
    if customer_type == "standard":
        return subtotal
    elif customer_type == "premium":
        if subtotal >= 100:
            return subtotal * 0.90
        else:
            return subtotal * 0.95
    elif customer_type == "vip":
        if subtotal >= 500:
            return subtotal * 0.80
        else:
            return subtotal * 0.85
    return subtotal

def calculate_total(cart, customer_type, tax_rate):
    subtotal = sum(item["subtotal"] for item in cart)
    discounted = apply_discount(subtotal, customer_type)
    tax = (discounted * tax_rate) / 100
    total = discounted + tax
    return round(total, 2)
"""

        env.step(Action(action_type=ActionType.DIAGNOSE, diagnosis=diagnosis, reasoning=diagnosis))
        result = env.step(Action(action_type=ActionType.SUBMIT_SOLUTION, final_solution=solution, reasoning="Applying fix"))
        results[task_id] = {"score": result.reward.value, "task_id": task_id}

    avg = sum(r["score"] for r in results.values()) / len(results)
    return {"baseline_scores": results, "average": round(avg, 3)}
