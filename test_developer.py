import json, os
from developer_agent import run_developer, validate_code

PLAN = os.path.join("artifacts", "plan.json")
OUT = os.path.join("artifacts", "navigation_logic.py")

def test_developer_pipeline():
    with open(PLAN, encoding="utf-8") as f:
        plan = json.load(f)

    code = run_developer(plan)
    validate_code(code)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(code)

    print(code)
    assert "def decide_next_move(" in code