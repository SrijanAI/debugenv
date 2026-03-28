# DebugEnv

> An OpenEnv-compliant environment for training and evaluating AI agents on real-world code debugging tasks.

Everyone is building with AI now — but AI isn't a great debugger yet. It ships code fast, full of silent bugs, wrong logic, and unhandled edge cases. **DebugEnv** is the missing benchmark: a gym where agents learn to actually find and fix bugs, not just generate more of them.

---

## Environment Description

DebugEnv simulates a developer's debugging workflow. The agent receives buggy code, observes errors and context, and must diagnose root causes and submit a correct fix. Rewards are shaped at every step — partial credit for correct diagnosis, more for correct fix, full credit only when tests pass.

**Three difficulty levels:**

| Task | Difficulty | Bug Type | Description |
|------|-----------|----------|-------------|
| `easy` | Easy | NameError (typo) | Variable name misspelled — obvious from traceback |
| `medium` | Medium | Silent logic bug | Wrong comparison operator — no error, wrong output |
| `hard` | Hard | Two-bug cascade | Date format crash + silent case-sensitivity bug |

---

## Action & Observation Spaces

### Observation
```json
{
  "task_id": "debug_easy_001",
  "difficulty": "easy",
  "code_snippet": "...",
  "error_message": "NameError: name 'discont_percent' is not defined",
  "stack_trace": "...",
  "language": "python",
  "context": "...",
  "available_actions": ["diagnose", "suggest_fix", "request_more_info", "submit_solution"],
  "step_number": 0,
  "max_steps": 5,
  "previous_attempts": []
}
```

### Action
```json
{
  "action_type": "diagnose",
  "diagnosis": "The variable 'discont_percent' is a typo of 'discount_percent'",
  "reasoning": "Line 3 references discont_percent which was never defined"
}
```

### Reward
```json
{
  "value": 0.5,
  "breakdown": {
    "identified_error_type": 0.2,
    "identified_typo": 0.3
  },
  "feedback": "Correctly identified the NameError. Found the typo.",
  "done": false
}
```

---

## Setup

### Local

```bash
git clone https://github.com/yourusername/debugenv
cd debugenv
pip install -r requirements.txt
uvicorn api.server:app --host 0.0.0.0 --port 7860
```

### Docker

```bash
docker build -t debugenv .
docker run -p 7860:7860 debugenv
```

### Baseline inference

```bash
export OPENAI_API_KEY=your_key_here
python baseline/inference.py
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/reset?task_id=easy` | POST | Reset env, return initial observation |
| `/step?task_id=easy` | POST | Take one step, return obs+reward+done |
| `/state?task_id=easy` | GET | Return current internal state |
| `/tasks` | GET | List all tasks + action schema |
| `/grader?task_id=easy` | POST | Return grader score for current episode |
| `/baseline` | POST | Run baseline agent on all 3 tasks |

---

## Baseline Scores

| Task | Score | Model |
|------|-------|-------|
| easy | 0.90 | gpt-4o-mini |
| medium | 0.65 | gpt-4o-mini |
| hard | 0.45 | gpt-4o-mini |
| **average** | **0.67** | gpt-4o-mini |

---

## Project Structure

```
debugenv/
├── environment/
│   ├── env.py              # Core DebugEnv class
│   ├── models.py           # Pydantic typed models
│   ├── scenarios/          # Task definitions + test cases
│   └── graders/            # Deterministic graders per task
├── api/
│   └── server.py           # FastAPI server
├── baseline/
│   └── inference.py        # OpenAI API baseline agent
├── openenv.yaml            # OpenEnv metadata
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Reward Shaping

Rewards are **not** binary. Every step provides signal:

- Diagnosing the correct error type → partial reward
- Identifying the root cause → more reward
- Suggesting the correct fix → more reward
- Submitting a solution that passes all tests → full reward
- Taking too many steps → small penalty

This ensures agents can learn from partial progress, not just end-of-episode outcomes.

---

## Built for the AI Vibe-Coding Era

The hard task specifically tests whether agents can find **silent bugs** — the kind AI code generators produce most often. A bug that doesn't crash but silently returns wrong results is far more dangerous in production than one that throws an exception. DebugEnv trains agents to catch both.
