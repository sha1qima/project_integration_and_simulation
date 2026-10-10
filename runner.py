

## Create a function to run the simulation of the navigation logic.
## It should define a set of scenarios with different states (e.g., front_blocked, left_blocked, right_blocked), expected outputs (e.g., FORWARD, LEFT, RIGHT, STOP), and then run the decide_next_move function on each scenario.
## The function should collect the results, including whether the actual output matches the expected output, and return a report summarizing the results.
## The report must include the total number of scenarios, the number of passed and failed scenarios, and a success rate, which is the number of passed scenarios divided by the total number of scenarios.


## If this script is run directly, run the simulation function and save the simulation report to a JSON file.
# runner.py

import json
import os
import importlib.util
from pathlib import Path


LOGIC_PATH = os.path.join("artifacts", "navigation_logic.py")
REPORT_PATH = os.path.join("artifacts", "simulation_report.json")


def _load_decide():
    spec = importlib.util.spec_from_file_location("nav", LOGIC_PATH)
    nav = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(nav)
    if not hasattr(nav, "decide_next_move"):
        raise RuntimeError("navigation_logic.py does not define decide_next_move")
    return nav.decide_next_move


# All possible scenarios (goal flags + blocked flags) with expected actions.
SCENARIOS = [
    # Goal-directed, clear paths
    ({"goal_ahead": True, "goal_on_left": False, "goal_on_right": False,
      "front_blocked": False, "left_blocked": False, "right_blocked": False},
     "FORWARD"),
    ({"goal_ahead": False, "goal_on_left": True, "goal_on_right": False,
      "front_blocked": False, "left_blocked": False, "right_blocked": False},
     "LEFT"),
    ({"goal_ahead": False, "goal_on_left": False, "goal_on_right": True,
      "front_blocked": False, "left_blocked": False, "right_blocked": False},
     "RIGHT"),

    # Goal direction blocked -> fallback
    ({"goal_ahead": True, "goal_on_left": False, "goal_on_right": False,
      "front_blocked": True, "left_blocked": False, "right_blocked": False},
     "LEFT"),
    ({"goal_ahead": True, "goal_on_left": False, "goal_on_right": False,
      "front_blocked": True, "left_blocked": True, "right_blocked": False},
     "RIGHT"),
    ({"goal_ahead": False, "goal_on_left": True, "goal_on_right": False,
      "front_blocked": False, "left_blocked": True, "right_blocked": False},
     "FORWARD"),
    ({"goal_ahead": False, "goal_on_left": False, "goal_on_right": True,
      "front_blocked": False, "left_blocked": False, "right_blocked": True},
     "FORWARD"),

    # All blocked -> STOP
    ({"goal_ahead": True, "goal_on_left": False, "goal_on_right": False,
      "front_blocked": True, "left_blocked": True, "right_blocked": True},
     "STOP"),
    ({"goal_ahead": False, "goal_on_left": False, "goal_on_right": False,
      "front_blocked": True, "left_blocked": True, "right_blocked": True},
     "STOP"),
]


def run_simulation():
    decide = _load_decide()

    results = []
    passed = 0
    failed = 0

    for i, (state, expected) in enumerate(SCENARIOS, start=1):
        try:
            actual = decide(state)
        except Exception as e:
            actual = f"ERROR: {e}"

        ok = (actual == expected)
        if ok:
            passed += 1
        else:
            failed += 1

        results.append({
            "scenario_id": i,
            "state": state,
            "expected": expected,
            "actual": actual,
            "passed": ok,
        })

    total = len(SCENARIOS)
    report = {
        "total_scenarios": total,
        "passed": passed,
        "failed": failed,
        "success_rate": passed / total if total else 0.0,
        "results": results,
    }
    return report


def main():
    os.makedirs("artifacts", exist_ok=True)
    report = run_simulation()
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nSimulation report saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()