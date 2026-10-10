
## Keep the original code, but update it as follows:
## Create a new function like run_developer_revision()
# This function will receive the original navigation code, the review notes, the benchmark report, the requirements and the plan. 
# Based on all of the above, this function will ask the LLM to generate a new navigation logic and then save that as a new file
# developer_agent.py

import json
import os
from openai import OpenAI

client = OpenAI(
    api_key="ollama",
    base_url="http://localhost:11434/v1",
)

MODEL = "qwen2.5:7b"

DEVELOPER_SYSTEM_PROMPT = """
You are a Developer Agent in a multi-agent robot navigation system.

Your job is to convert a navigation plan (JSON) into a single Python
function called `decide_next_move(state)`.

Strict rules:
1. Output ONLY Python code. No markdown fences. No explanations.
2. The code MUST define exactly one function:

    def decide_next_move(state):
        ...

3. `state` is a dict with these EXACT boolean keys:
   "goal_ahead", "goal_on_left", "goal_on_right",
   "front_blocked", "left_blocked", "right_blocked"

4. The function must return one of these strings ONLY:
   "FORWARD", "LEFT", "RIGHT", "STOP"

5. Implement the decisions in the plan IN ORDER, from most specific
   to most general. The first matching decision wins.

6. Do NOT import anything. Do NOT print anything. Do NOT add a main block.

7. Always include a final fallback: if all three directions are blocked,
   return "STOP".
""".strip()

REVISION_SYSTEM_PROMPT = """
You are a Developer Agent performing a REVISION of previously generated
navigation logic. You receive:
  - the original navigation code,
  - the review notes (from the Reviewer / Benchmark Reviewer),
  - the benchmark report,
  - the requirements artifact,
  - the plan artifact.

Your job is to produce an IMPROVED version of the `decide_next_move(state)`
function that fixes the issues identified in the review while staying
consistent with the requirements and the plan.

Strict rules:
1. Output ONLY Python code. No markdown fences. No explanations.
2. The code MUST define exactly one function:

    def decide_next_move(state):
        ...

3. `state` is a dict with these EXACT boolean keys:
   "goal_ahead", "goal_on_left", "goal_on_right",
   "front_blocked", "left_blocked", "right_blocked"

4. The function must return one of these strings ONLY:
   "FORWARD", "LEFT", "RIGHT", "STOP"

5. Preserve the correct behavior already working, and fix the issues
   raised in the review notes and benchmark report.

6. Do NOT import anything. Do NOT print anything. Do NOT add a main block.

7. Always guarantee: if all three directions are blocked, return "STOP".
   Never return "STOP" if at least one direction is unblocked.
""".strip()


def _strip_code_fence(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def validate_code(code):
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Generated code must be a non-empty string.")

    if code.strip().startswith("```"):
        raise ValueError("Code must not contain markdown fences.")

    if "def decide_next_move(" not in code:
        raise ValueError("Code must define 'decide_next_move(state)'.")

    for token in ('"FORWARD"', "'FORWARD'",
                  '"LEFT"', "'LEFT'",
                  '"RIGHT"', "'RIGHT'",
                  '"STOP"', "'STOP'"):
        if token in code:
            break
    else:
        raise ValueError("Code must return one of FORWARD/LEFT/RIGHT/STOP.")

    if "import " in code:
        raise ValueError("Code must not contain import statements.")

    return True


def _call_llm(system_prompt, user_message):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content.strip()


def run_developer(plan):
    if not isinstance(plan, dict):
        raise TypeError("plan must be a dictionary.")

    user_message = (
        "Here is the navigation plan (JSON):\n"
        f"{json.dumps(plan, indent=2)}\n\n"
        "Generate the Python code for `decide_next_move(state)` now."
    )

    raw = _call_llm(DEVELOPER_SYSTEM_PROMPT, user_message)
    code = _strip_code_fence(raw)
    validate_code(code)
    return code


def run_developer_revision(original_code, review_notes, benchmark_report,
                            requirements, plan):
    """
    Generate a revised navigation logic based on:
      - original_code : str, the previously generated navigation logic
      - review_notes  : dict, output of the Reviewer / Benchmark Reviewer
      - benchmark_report : dict, output of the IR-SIM benchmark
      - requirements  : dict, the requirements artifact
      - plan          : dict, the planner artifact

    Returns the revised Python code (validated) as a string.
    """
    if not isinstance(original_code, str) or not original_code.strip():
        raise ValueError("original_code must be a non-empty string.")

    user_message = (
        "=== ORIGINAL NAVIGATION CODE ===\n"
        f"{original_code}\n\n"
        "=== REVIEW NOTES ===\n"
        f"{json.dumps(review_notes, indent=2, ensure_ascii=False)}\n\n"
        "=== BENCHMARK REPORT ===\n"
        f"{json.dumps(benchmark_report, indent=2, ensure_ascii=False)}\n\n"
        "=== REQUIREMENTS ===\n"
        f"{json.dumps(requirements, indent=2, ensure_ascii=False)}\n\n"
        "=== PLAN ===\n"
        f"{json.dumps(plan, indent=2, ensure_ascii=False)}\n\n"
        "Produce the REVISED `decide_next_move(state)` function now. "
        "Fix the issues described in the review notes and benchmark report, "
        "while preserving the correct behavior."
    )

    raw = _call_llm(REVISION_SYSTEM_PROMPT, user_message)
    code = _strip_code_fence(raw)
    validate_code(code)
    return code