import json
import os
import subprocess
import sys


## Import all the necessary functions from other modules to run the entire pipeline.
# main.py

import json
import os
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Add project root to path so imports work
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from analyst_agent import run_analyst
from planner_agent import run_planner
from developer_agent import run_developer, run_developer_revision
from test_agent import run_test_agent
from reviewer_agent import run_reviewer
from reviewer_benchmark_agent import run_benchmark_reviewer
import runner as simulation_runner

ARTIFACTS = BASE_DIR / "artifacts"
LOG_PATH = BASE_DIR / "trace.log"
BRIEF_PATH = BASE_DIR / "brief.txt"

## Write a main function to run the entire pipeline.
## It should create necessary directories, or check that it exists, 
# Then run each agent in sequence, save their outputs to files, and log events.
# Logging events should include the name of the agent and the action taken, such as "Analyst Agent created requirements.json".
def log(agent, action):
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {agent}: {action}"
    print(line)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def run_cmd(cmd, cwd=None):
    """Run a subprocess, stream output, return (returncode, stdout+stderr)."""
    proc = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True,
    )
    output = proc.stdout + proc.stderr
    return proc.returncode, output


def main():
    ARTIFACTS.mkdir(exist_ok=True)

    # Reset log for a fresh run
    with LOG_PATH.open("w", encoding="utf-8") as f:
        f.write(f"=== Pipeline run started at {datetime.now().isoformat()} ===\n")

    # ---------------- 1. Load brief ----------------
    log("Orchestrator", "Loading brief.txt")
    brief_text = BRIEF_PATH.read_text(encoding="utf-8")

    # ---------------- 2. Analyst Agent ----------------
    log("Analyst Agent", "Creating requirements.json")
    requirements = run_analyst(brief_text)
    save_json(ARTIFACTS / "requirements.json", requirements)
    log("Analyst Agent", "requirements.json created")

    # ---------------- 3. Planner Agent ----------------
    log("Planner Agent", "Creating plan.json")
    plan = run_planner(requirements)
    save_json(ARTIFACTS / "plan.json", plan)
    log("Planner Agent", "plan.json created")

    # ---------------- 4. Developer Agent ----------------
    log("Developer Agent", "Creating navigation_logic.py")
    code = run_developer(plan)
    (ARTIFACTS / "navigation_logic.py").write_text(code, encoding="utf-8")
    # Also write to generated/ because test_irsim_with_agent imports from there
    gen_dir = BASE_DIR / "generated"
    gen_dir.mkdir(exist_ok=True)
    (gen_dir / "navigation_logic.py").write_text(code, encoding="utf-8")
    log("Developer Agent", "navigation_logic.py created")

    # ---------------- 5. Test Agent ----------------
    log("Test Agent", "Creating test_generated_navigation_logic.py")
    test_code = run_test_agent(requirements, plan, code)
    (BASE_DIR / "test_generated_navigation_logic.py").write_text(
        test_code, encoding="utf-8"
    )
    log("Test Agent", "test_generated_navigation_logic.py created")

    # Run the generated tests
    log("Test Agent", "Running generated pytest tests")
    rc, out = run_cmd(
        [sys.executable, "-m", "pytest", "-q",
         "test_generated_navigation_logic.py"],
        cwd=str(BASE_DIR),
    )
    (ARTIFACTS / "test_agent_output.txt").write_text(out, encoding="utf-8")
    log("Test Agent", f"pytest exited with code {rc}")

    # ---------------- 6. Simulation Runner ----------------
    log("Simulation Runner", "Running runner.py -> simulation_report.json")
    sim_report = simulation_runner.run_simulation()
    save_json(ARTIFACTS / "simulation_report.json", sim_report)
    log("Simulation Runner",
        f"simulation_report.json created (passed={sim_report['passed']}, "
        f"failed={sim_report['failed']})")

    # ---------------- 7. Reviewer Agent ----------------
    log("Reviewer Agent", "Creating review.json")
    review = run_reviewer(sim_report)
    save_json(ARTIFACTS / "review.json", review)
    log("Reviewer Agent",
        f"review.json created (needs_revision={review['needs_revision']})")

    # ---------------- 8. IR-SIM Benchmark ----------------
    log("IR-SIM Benchmark", "Running benchmark_irsim.py")
    rc, out = run_cmd(
        [sys.executable, "benchmark_irsim.py"],
        cwd=str(BASE_DIR),
    )
    log("IR-SIM Benchmark", f"benchmark_irsim.py exited with code {rc}")

    benchmark_path = ARTIFACTS / "irsim_benchmark_report.json"
    if benchmark_path.exists():
        benchmark_report = json.loads(benchmark_path.read_text(encoding="utf-8"))
    else:
        benchmark_report = {}
        save_json(benchmark_path, benchmark_report)

    log("IR-SIM Benchmark", "irsim_benchmark_report.json created")

    # ---------------- 9. Benchmark Reviewer ----------------
    log("Benchmark Reviewer", "Creating benchmark_review.json")
    bench_review = run_benchmark_reviewer(benchmark_report)
    save_json(ARTIFACTS / "benchmark_review.json", bench_review)
    log("Benchmark Reviewer",
        f"benchmark_review.json created (needs_revision={bench_review['needs_revision']})")

    # ---------------- 10. Developer Revision (if needed) ----------------
    needs_revision = (
        review.get("needs_revision", False)
        or bench_review.get("needs_revision", False)
    )

    if needs_revision:
        log("Developer Agent", "Revision requested - running run_developer_revision()")
        try:
            revised_code = run_developer_revision(
                original_code=code,
                review_notes=review,
                benchmark_report=benchmark_report,
                requirements=requirements,
                plan=plan,
            )
            revised_path = ARTIFACTS / "navigation_logic_revised.py"
            revised_path.write_text(revised_code, encoding="utf-8")
            (gen_dir / "navigation_logic.py").write_text(
                revised_code, encoding="utf-8"
            )
            log("Developer Agent",
                f"navigation_logic_revised.py created at {revised_path}")

            # Re-run simulation on revised logic
            log("Simulation Runner",
                "Re-running simulation on revised navigation logic")
            # Point runner at revised file
            simulation_runner.LOGIC_PATH = str(revised_path)
            sim_report2 = simulation_runner.run_simulation()
            save_json(ARTIFACTS / "simulation_report_revised.json", sim_report2)
            log("Simulation Runner",
                f"simulation_report_revised.json created "
                f"(passed={sim_report2['passed']}, failed={sim_report2['failed']})")

            # Re-run IR-SIM benchmark on revised logic
            log("IR-SIM Benchmark",
                "Re-running IR-SIM benchmark on revised navigation logic")
            rc, out = run_cmd(
                [sys.executable, "benchmark_irsim.py"],
                cwd=str(BASE_DIR),
            )
            log("IR-SIM Benchmark",
                f"Re-run benchmark_irsim.py exited with code {rc}")

            if benchmark_path.exists():
                benchmark_report2 = json.loads(
                    benchmark_path.read_text(encoding="utf-8")
                )
                save_json(ARTIFACTS / "irsim_benchmark_report_revised.json",
                          benchmark_report2)
                bench_review2 = run_benchmark_reviewer(benchmark_report2)
                save_json(ARTIFACTS / "benchmark_review_revised.json",
                          bench_review2)
                log("Benchmark Reviewer",
                    "benchmark_review_revised.json created")
        except Exception as e:
            log("Developer Agent", f"Revision failed: {e}")
            traceback.print_exc()
    else:
        log("Orchestrator", "No revision needed - all checks passed")

    log("Orchestrator", "Pipeline completed successfully")


if __name__ == "__main__":
    main()