
### Create a system prompt that instructs the Test Agent to generate pytest-style tests for the decide_next_move function, 
# based on the requirements and plan provided. 
# The prompt should specify the expected input structure and required test coverage, 
# while also enforcing constraints on the output format.
# test_agent.py

# test_agent.py

import json
from openai import OpenAI

client = OpenAI(
    api_key="ollama",
    base_url="http://localhost:11434/v1",
)

MODEL = "qwen2.5:7b"

TEST_AGENT_SYSTEM_PROMPT = """
You are the Test Agent in a multi-agent robot navigation system.

You receive:
  - the requirements artifact (JSON),
  - the plan artifact (JSON),
  - the generated navigation code (Python).

Your job: produce a complete pytest-style test file that thoroughly
tests the `decide_next_move(state)` function.

Strict rules:
1. Output ONLY Python test code. No markdown fences. No explanations.
2. The test file MUST start with:

    import importlib.util
    import os
    import pytest

3. It MUST define a loader that loads `artifacts/navigation_logic.py`
   and returns the `decide_next_move` function.
4. It MUST use `@pytest.mark.parametrize` with a list of (state, expected)
   tuples.
5. It MUST cover AT LEAST these scenarios:
   - goal_ahead + front clear -> FORWARD
   - goal_on_left + left clear -> LEFT
   - goal_on_right + right clear -> RIGHT
   - front blocked, left clear -> LEFT
   - front blocked, right clear -> RIGHT
   - all blocked -> STOP
   - goal direction blocked but another clear -> fallback (FORWARD/LEFT/RIGHT)
6. Each test MUST assert that the returned action is one of
   {"FORWARD", "LEFT", "RIGHT", "STOP"} and equals the expected action.
7. Do NOT include any `if __name__ == "__main__"` block.
8. The file must be syntactically valid Python.
""".strip()

## Write a function to validate the generated test code. 
# It should check that the code is a non-empty string, does not contain markdown fences, 
# Also check that the test code includes all the necessary keywords like the import statements and test assertions.
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


def validate_test_code(code):
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Generated test code must be a non-empty string.")

    if "```" in code:
        raise ValueError("Test code must not contain markdown fences.")

    required_tokens = [
        "import importlib.util",
        "import os",
        "import pytest",
        "decide_next_move",
        "@pytest.mark.parametrize",
        "assert",
    ]
    for token in required_tokens:
        if token not in code:
            raise ValueError(f"Test code is missing required token: {token!r}")

    try:
        compile(code, "<generated_test>", "exec")
    except SyntaxError as e:
        raise ValueError(f"Generated test code has a syntax error: {e}")

    return True

## Write a function to run the Test Agent. 
# It should take in requirements and a plan, send them to the Test Agent.
# Thefunction must return the generated test code after validation.

def run_test_agent(requirements, plan, navigation_code):
    if not isinstance(requirements, dict):
        raise TypeError("requirements must be a dictionary.")
    if not isinstance(plan, dict):
        raise TypeError("plan must be a dictionary.")
    if not isinstance(navigation_code, str) or not navigation_code.strip():
        raise ValueError("navigation_code must be a non-empty string.")

    user_message = (
        "=== REQUIREMENTS ===\n"
        f"{json.dumps(requirements, indent=2, ensure_ascii=False)}\n\n"
        "=== PLAN ===\n"
        f"{json.dumps(plan, indent=2, ensure_ascii=False)}\n\n"
        "=== NAVIGATION CODE ===\n"
        f"{navigation_code}\n\n"
        "Produce the pytest test file now. Remember: output ONLY Python code, "
        "no markdown fences, no ``` blocks."
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": TEST_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.0,
    )

    raw = response.choices[0].message.content.strip()

    raw = _strip_code_fence(raw)

    validate_test_code(raw)
    return raw