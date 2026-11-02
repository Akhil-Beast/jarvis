import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.brain import brain

queries = [
    "how to open chrome",
    "tell me how to take a screenshot",
    "create a folder named my_project",
    "how to execute task open solidworks",
    "type hello world this is a test",
    "can you please increase the volume",
    "what time is it",
]

print("=== TESTING AUTONOMOUS ACTION EXECUTION (NO PASSIVE TUTORIALS) ===")
for q in queries:
    plan = brain.plan_command(q)
    print(f"\nQUERY: '{q}'")
    print(f"PLAN EXPLANATION: {plan.explanation}")
    has_action = any(s.get("action") != "speak" for s in plan.steps)
    print(f"HAS CONCRETE ACTION: {'YES' if has_action or q == 'what time is it' else 'NO (FAIL)'}")
    for i, s in enumerate(plan.steps):
        print(f"  Step {i+1}: {s}")
