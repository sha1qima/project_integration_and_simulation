import json, os
from planner_agent import run_planner, validate_plan

REQ = os.path.join("artifacts", "requirements.json")
OUT = os.path.join("artifacts", "plan.json")

def test_planner_pipeline():
    with open(REQ, encoding="utf-8") as f:
        req = json.load(f)

    plan = run_planner(req)
    validate_plan(plan)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print(json.dumps(plan, ensure_ascii=False, indent=2))
    assert "strategy" in plan and "decisions" in plan and "stop_condition" in plan