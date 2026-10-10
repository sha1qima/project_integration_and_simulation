# analyst_agent.py

import json
import os
from openai import OpenAI

client = OpenAI(
    api_key="ollama",
    base_url="http://localhost:11434/v1",
)

MODEL = "qwen2.5:7b"

REQUIRED_KEYS = {"goal", "allowed_actions", "safe_stop", "avoid_obstacles"}
ALLOWED_ACTIONS = {"FORWARD", "LEFT", "RIGHT", "STOP"}

SYSTEM_PROMPT = """
You are a requirements analyst agent.

Your ONLY job is to read a human-language brief about a mobile robot
and convert it into explicit software requirements.

Rules you MUST follow:
1. The robot navigation system can ONLY use these actions:
   FORWARD, LEFT, RIGHT, STOP.
   Never introduce any other action.
2. Output MUST be a single valid JSON object. No explanation, no markdown,
   no code fences, no extra text.
3. The JSON must use EXACTLY this structure and these key names:

{
  "goal": "string describing the navigation objective",
  "allowed_actions": ["FORWARD", "LEFT", "RIGHT", "STOP"],
  "safe_stop": true,
  "avoid_obstacles": true
}

4. "goal" is a string.
5. "allowed_actions" is a list of strings, only from the four actions above.
6. "safe_stop" is a boolean: true if the robot must stop safely when it
   cannot move anywhere, otherwise false.
7. "avoid_obstacles" is a boolean: true if the robot must avoid blocked
   directions, otherwise false.
8. Do NOT add any extra keys. Do NOT remove any keys.
""".strip()


def _call_qwen(brief_text):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": brief_text},
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content.strip()


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


def validate_requirements(result):
    if not isinstance(result, dict):
        raise ValueError("Requirements must be a dictionary.")

    keys = set(result.keys())
    if keys != REQUIRED_KEYS:
        missing = REQUIRED_KEYS - keys
        extra = keys - REQUIRED_KEYS
        raise ValueError("Key mismatch. Missing=%s, Extra=%s" % (missing, extra))

    if not isinstance(result["goal"], str):
        raise ValueError("'goal' must be a string.")

    if not isinstance(result["allowed_actions"], list):
        raise ValueError("'allowed_actions' must be a list.")

    for action in result["allowed_actions"]:
        if not isinstance(action, str) or action not in ALLOWED_ACTIONS:
            raise ValueError(
                "Invalid action: %r. Only %s are allowed."
                % (action, sorted(ALLOWED_ACTIONS))
            )

    if not isinstance(result["safe_stop"], bool):
        raise ValueError("'safe_stop' must be a boolean.")

    if not isinstance(result["avoid_obstacles"], bool):
        raise ValueError("'avoid_obstacles' must be a boolean.")

    return True


def run_analyst(brief_text):
    raw = _call_qwen(brief_text)
    cleaned = _strip_code_fence(raw)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError("Qwen did not return valid JSON: %s\nRaw:\n%s" % (e, raw))

    validate_requirements(data)
    return data