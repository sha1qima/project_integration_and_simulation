import json
import os
import subprocess
import sys
import ast
from pathlib import Path
## Load the world files for the IR-SIM benchmark.
# benchmark_irsim.py

WORLDS = [
    "irsim_worlds/world_easy.yaml",
    "irsim_worlds/world_medium.yaml",
    "irsim_worlds/world_hard.yaml",
    "irsim_worlds/world_custom.yaml",
]

REPORT_PATH = os.path.join("artifacts", "irsim_benchmark_report.json")
IRSIM_REPORT_PATH = os.path.join("artifacts", "irsim_report.json")
EFFICIENT_STEP_LIMIT = 200

## Create a function to run the IR-SIM benchmark for a given world file.
## It should call the test_irsim_with_agent.py script with the world file as an argument, capture the output, and extract the report from the output.
def run_world(world_file):
    """Run test_irsim_with_agent.py for a world and return the parsed report."""

    if os.path.exists(IRSIM_REPORT_PATH):
        os.remove(IRSIM_REPORT_PATH)

    env = os.environ.copy()
    env["MPLBACKEND"] = "Agg"

    result = subprocess.run(
        [sys.executable, "test_irsim_with_agent.py", world_file],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )

    output = result.stdout + result.stderr

    report = None
    if os.path.exists(IRSIM_REPORT_PATH):
        try:
            with open(IRSIM_REPORT_PATH, "r", encoding="utf-8") as f:
                report = json.load(f)
        except Exception:
            report = None

    if report is None:
        marker = "IR-SIM report:"
        if marker in output:
            tail = output.split(marker, 1)[1]
            start = tail.find("{")
            if start != -1:
                depth = 0
                end = start
                for i in range(start, len(tail)):
                    if tail[i] == "{":
                        depth += 1
                    elif tail[i] == "}":
                        depth -= 1
                        if depth == 0:
                            end = i
                            break
                try:
                    report = ast.literal_eval(tail[start:end + 1])
                except Exception:
                    report = None

    if report is None:
        report = {
            "reached_goal": False,
            "collision_or_done": True,
            "steps_taken": 300,
            "efficiency_status": "failed",
        }

    report["world"] = world_file
    return report


## Create a main function to run the IR-SIM benchmark for all world files and generate a summary report.
## The summary report should include the total number of worlds, the number of worlds where the goal was reached, the success rate, the number of efficient worlds, the number of inefficient but successful worlds, the number of failed worlds, the efficiency rate, and the average steps taken across all worlds. The report should be saved to a JSON file.
## The benchmark report must have the following structure:
""" benchmark_report = {
        "total_worlds": total,
        "goals_reached": reached_goal_count,
        "success_rate": reached_goal_count / total,
        "efficient_worlds": efficient_count,
        "inefficient_success_worlds": inefficient_success_count,
        "failed_worlds": failed_count,
        "efficiency_rate": efficient_count / total,
        "average_steps_taken": average_steps,
        "results": results
    } """
## Save the benchmark report to a JSON file named "irsim_benchmark_report.json" under the artifacts folder, and print the report to the console in a readable format.
def main():
    os.makedirs("artifacts", exist_ok=True)

    results = []
    reached_goal_count = 0
    efficient_count = 0
    inefficient_success_count = 0
    failed_count = 0
    total_steps = 0

    for world in WORLDS:
        if not os.path.exists(world):
            print(f"[SKIP] {world} not found")
            continue

        print(f"\n=== Running {world} ===")
        report = run_world(world)
        print(f"    -> {report}")

        reached = bool(report.get("reached_goal", False))
        steps = int(report.get("steps_taken", 0))
        efficiency_status = report.get(
            "efficiency_status",
            "efficient" if reached and steps <= EFFICIENT_STEP_LIMIT else
            ("acceptable_but_inefficient" if reached else "failed"),
        )

        if reached:
            reached_goal_count += 1
            if efficiency_status == "efficient":
                efficient_count += 1
            else:
                inefficient_success_count += 1
        else:
            failed_count += 1

        total_steps += steps
        results.append(report)

    total = len(results) if results else 1

    benchmark_report = {
        "total_worlds": len(results),
        "goals_reached": reached_goal_count,
        "success_rate": reached_goal_count / total,
        "efficient_worlds": efficient_count,
        "inefficient_success_worlds": inefficient_success_count,
        "failed_worlds": failed_count,
        "efficiency_rate": efficient_count / total,
        "average_steps_taken": total_steps / total,
        "results": results,
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(benchmark_report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("IR-SIM BENCHMARK REPORT")
    print("=" * 60)
    print(json.dumps(benchmark_report, indent=2, ensure_ascii=False))
    print(f"\nSaved to {REPORT_PATH}")


if __name__ == "__main__":
    main()