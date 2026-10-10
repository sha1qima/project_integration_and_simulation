import json
from pathlib import Path
from planner_agent import run_planner

## Reads requirements from requirements.json, calls run_planner, and writes plan.json.
def main():
    base_dir = Path(__file__).parent
    artifacts = base_dir / "artifacts"
    artifacts.mkdir(exist_ok=True)

    requirements_path = artifacts / "requirements.json"
    plan_path = artifacts / "plan.json"

    with requirements_path.open("r", encoding="utf-8") as f:
        requirements = json.load(f)

    plan = run_planner(requirements)

    with plan_path.open("w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    print(f"Validated plan written to {plan_path}")


if __name__ == "__main__":
    main()