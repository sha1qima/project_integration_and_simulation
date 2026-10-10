## Create a system prompt for the Reviewer Agent that instructs it to analyze the simulation report and output a JSON object with specific keys.
## The JSON object it outputs must follow a strict schema and contain keys "issue", "likely_cause", "recommendation", and "needs_revision".
## The Reviewer Agent should validate the output to ensure it adheres to the schema and that "needs_revision" is a boolean.
# reviewer_agent.py

import json
from openai import OpenAI

client = OpenAI(
    api_key="ollama",
    base_url="http://localhost:11434/v1",
)

MODEL = "qwen2.5:7b"

REVIEWER_SYSTEM_PROMPT = """
You are the Reviewer Agent in a multi-agent robot navigation system.

You receive a simulation report produced by the Simulation Runner.
The report describes how many scenarios passed/failed and lists the
individual scenario results.

Your job: analyze the report and produce a SINGLE JSON object with
EXACTLY these keys:

{
  "issue": "<string describing the main problem found, or 'None' if all passed>",
  "likely_cause": "<string describing the likely cause of the issue>",
  "recommendation": "<string describing how to fix it>",
  "needs_revision": <boolean>
}

Rules:
1. Output ONLY the JSON object. No markdown, no code fences, no extra text.
2. "issue", "likely_cause", "recommendation" must be non-empty strings.
3. "needs_revision" must be a boolean: true if any scenario failed,
   false if all scenarios passed.
4. Do NOT add any extra keys.
""".strip()

REQUIRED_KEYS = {"issue", "likely_cause", "recommendation", "needs_revision"}

## Create a function to validate the output of the Reviewer Agent.
## It should check that the output is a JSON object with the required keys and that "needs_revision" is a boolean, and the rest of the keys are strings.
def validate_review(data):
    if not isinstance(data, dict):
        raise ValueError("Review must be a dictionary.")

    if set(data.keys()) != REQUIRED_KEYS:
        raise ValueError(
            f"Review must contain exactly {REQUIRED_KEYS}, got {set(data.keys())}"
        )

    for key in ("issue", "likely_cause", "recommendation"):
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError(f"'{key}' must be a non-empty string.")

    if not isinstance(data["needs_revision"], bool):
        raise ValueError("'needs_revision' must be a boolean.")

    return True


## Create a function to run the Reviewer Agent.
## It should take in the simulation report, send it to the Reviewer Agent, and return the validated output.
def run_reviewer(simulation_report):
    if not isinstance(simulation_report, dict):
        raise TypeError("simulation_report must be a dictionary.")

    user_message = (
        "Here is the simulation report:\n"
        f"{json.dumps(simulation_report, indent=2, ensure_ascii=False)}\n\n"
        "Produce the review JSON now."
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.0,
    )

    raw = response.choices[0].message.content.strip()

    # strip code fences defensively
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
        raise ValueError(f"Reviewer did not return valid JSON: {e}\nRaw: {raw}")

    validate_review(data)
    return data