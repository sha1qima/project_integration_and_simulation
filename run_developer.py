import json
from pathlib import Path
from developer_agent import run_developer

def main():
    base_dir = Path(__file__).parent
    artifacts = base_dir / "artifacts"
    artifacts.mkdir(exist_ok=True)

    plan_path = artifacts / "plan.json"
    logic_path = artifacts / "navigation_logic.py"

    with plan_path.open("r", encoding="utf-8") as f:
        plan = json.load(f)

    code = run_developer(plan)

    with logic_path.open("w", encoding="utf-8") as f:
        f.write(code)

    print(f"Generated navigation logic written to {logic_path}")


if __name__ == "__main__":
    main()