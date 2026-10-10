

## Create a system prompt for the Reviewer Agent that instructs it to analyze the IR-SIM Benchmark report and output a JSON object with specific keys.
## The JSON object it outputs must follow a strict schema and contain keys "issue", "likely_cause", "recommendation", "safety_passed", "goal_completion_passed", "efficiency_passed", and "needs_revision".
## The Reviewer Agent should validate the output to ensure it adheres to the schema and that "safety_passed", "goal_completion_passed", "efficiency_passed", and "needs_revision" are booleans.
# reviewer_benchmark_agent.py

import json
from openai import OpenAI

client = OpenAI(
    api_key="ollama",
    base_url="http://localhost:11434/v1",
)

MODEL = "qwen2.5:7b"

BENCHMARK_REVIEWER_SYSTEM_PROMPT = """
You are the Benchmark Reviewer Agent in a multi-agent robot navigation
system.

You receive:
  - a deterministic review (computed by the pipeline) that already
    contains the correct pass/fail booleans, and
  - the raw IR-SIM benchmark report.

Your job: produce a SINGLE JSON object with EXACTLY these keys:

{
  "issue": "<string>",
  "likely_cause": "<string>",
  "recommendation": "<string>",
  "safety_passed": <boolean>,
  "goal_completion_passed": <boolean>,
  "efficiency_passed": <boolean>,
  "needs_revision": <boolean>
}

Rules:
1. Output ONLY the JSON object. No markdown, no code fences, no extra text.
2. "issue", "likely_cause", "recommendation" must be non-empty strings.
3. The four booleans MUST match the values in the deterministic review.
4. Do NOT add any extra keys.
""".strip()

REQUIRED_KEYS = {
    "issue", "likely_cause", "recommendation",
    "safety_passed", "goal_completion_passed",
    "efficiency_passed", "needs_revision",
}

## Create a function to validate the output of the Reviewer Agent for the benchmark report.
## It should check that the output is a JSON object with the required keys and that "safety_passed", "goal_completion_passed", "efficiency_passed", and "needs_revision" are booleans, and the rest of the keys are strings.
## If the output does not meet these criteria, raise a ValueError.
def validate_benchmark_review(data):
    if not isinstance(data, dict):
        raise ValueError("Benchmark review must be a dictionary.")

    if set(data.keys()) != REQUIRED_KEYS:
        raise ValueError(
            f"Benchmark review must contain exactly {REQUIRED_KEYS}, "
            f"got {set(data.keys())}"
        )

    for key in ("issue", "likely_cause", "recommendation"):
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError(f"'{key}' must be a non-empty string.")

    for key in ("safety_passed", "goal_completion_passed",
                "efficiency_passed", "needs_revision"):
        if not isinstance(data[key], bool):
            raise ValueError(f"'{key}' must be a boolean.")

    return True

## Create a function to build a deterministic review from the benchmark report.
## This function analyzes the benchmark report and determines the values for "safety_passed", "goal_completion_passed", "efficiency_passed", and "needs_revision" based on the measured benchmark fields.
## It returns a dictionary with the keys "issue", "likely_cause", "recommendation", "safety_passed", "goal_completion_passed", "efficiency_passed", and "needs_revision".
## If the benchmark report does not contain the required fields, default values will be used.
## If safety_passed is false, the issue will be described as "Unsafe benchmark behavior detected". Safety is measured as any world having collision_or_done true while reached_goal is false.
## If goal_completion_passed is false, the issue will be described as "Goal completion failure". Goal completion is measured as success_rate being less than 1.0.
## If efficiency_passed is false, the issue will be described as "Successful but inefficient navigation". Efficiency is measured as inefficient_success_worlds being greater than 0 or efficiency_rate being less than 1.0.
def build_deterministic_review(benchmark_report):
    """
    Build a deterministic review from the benchmark report.

    Safety: any world with collision_or_done True while reached_goal False.
    Goal completion: success_rate >= 1.0.
    Efficiency: no inefficient_success_worlds and efficiency_rate >= 1.0.
    """
    if not isinstance(benchmark_report, dict):
        benchmark_report = {}

    results = benchmark_report.get("results", []) or []
    total = benchmark_report.get("total_worlds", len(results)) or 0
    reached = benchmark_report.get("goals_reached", 0)
    success_rate = benchmark_report.get("success_rate", 0.0)
    inefficient = benchmark_report.get("inefficient_success_worlds", 0)
    efficiency_rate = benchmark_report.get("efficiency_rate", 0.0)

    # Safety: any collision while not reaching goal
    safety_violation = False
    for r in results:
        if r.get("collision_or_done", False) and not r.get("reached_goal", False):
            safety_violation = True
            break

    safety_passed = not safety_violation
    goal_completion_passed = (success_rate >= 1.0)
    efficiency_passed = (inefficient == 0) and (efficiency_rate >= 1.0)

    issues = []
    causes = []
    recommendations = []

    if not safety_passed:
        issues.append("Unsafe benchmark behavior detected")
        causes.append("Robot collided with an obstacle without reaching the goal")
        recommendations.append(
            "Improve obstacle avoidance and ensure safe STOP when all directions are blocked"
        )

    if not goal_completion_passed:
        issues.append("Goal completion failure")
        causes.append(
            f"Only {reached}/{total} worlds reached the goal (success_rate={success_rate:.2f})"
        )
        recommendations.append(
            "Review goal-directed decisions and ensure the robot does not get stuck"
        )

    if not efficiency_passed:
        issues.append("Successful but inefficient navigation")
        causes.append(
            f"{inefficient} worlds were successful but inefficient "
            f"(efficiency_rate={efficiency_rate:.2f})"
        )
        recommendations.append(
            "Reduce unnecessary turns/steps; prefer direct goal-directed motion"
        )

    if not issues:
        issue = "None"
        likely_cause = "None"
        recommendation = "None"
    else:
        issue = "; ".join(issues)
        likely_cause = "; ".join(causes)
        recommendation = "; ".join(recommendations)

    needs_revision = not (safety_passed and goal_completion_passed and efficiency_passed)

    return {
        "issue": issue,
        "likely_cause": likely_cause,
        "recommendation": recommendation,
        "safety_passed": safety_passed,
        "goal_completion_passed": goal_completion_passed,
        "efficiency_passed": efficiency_passed,
        "needs_revision": needs_revision,
    }

## Create a function to run the Reviewer Agent for the benchmark report.
## It should take in the benchmark report, build a deterministic review, send both to the Reviewer Agent, and return the validated output.
## The deterministic review is used to ensure that the pass/fail booleans in the output are based on the measured benchmark results, even if the LLM phrases the issue, likely cause, and recommendation.
## The output of this function will be a dictionary with the keys "issue", "likely_cause", "recommendation", "safety_passed", "goal_completion_passed", "efficiency_passed", and "needs_revision".
def run_benchmark_reviewer(benchmark_report):
    deterministic = build_deterministic_review(benchmark_report)

    user_message = (
        "=== DETERMINISTIC REVIEW (authoritative booleans) ===\n"
        f"{json.dumps(deterministic, indent=2, ensure_ascii=False)}\n\n"
        "=== RAW BENCHMARK REPORT ===\n"
        f"{json.dumps(benchmark_report, indent=2, ensure_ascii=False)}\n\n"
        "Produce the benchmark review JSON now. The four booleans MUST "
        "match the deterministic review."
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": BENCHMARK_REVIEWER_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.0,
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Benchmark Reviewer did not return valid JSON: {e}\nRaw: {raw}"
        )

    # Enforce deterministic booleans
    for key in ("safety_passed", "goal_completion_passed",
                "efficiency_passed", "needs_revision"):
        data[key] = deterministic[key]

    validate_benchmark_review(data)
    return data