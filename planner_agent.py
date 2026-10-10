import json
from ollama import chat

PLANNER_SYSTEM_PROMPT = """
You are the Planner Agent in a multi-agent robot navigation system.

Your role: Given a validated requirement artifact produced by the Analyst Agent,
decide HOW the robot should behave in order to achieve the goal.

You must NOT ask questions and you must NOT explain. Output ONLY a single JSON
object, with no markdown fences, no comments, and no extra text.

The robot receives a `state` dict with these EXACT boolean keys:
  "goal_ahead", "goal_on_left", "goal_on_right",
  "front_blocked", "left_blocked", "right_blocked"

The JSON object MUST have exactly this structure:

{
  "strategy": "<a short string describing the navigation strategy>",
  "decisions": [
    {
      "condition": "<a string describing when this decision applies>",
      "action": "<one of FORWARD, LEFT, RIGHT, STOP>"
    }
  ],
  "stop_condition": "<a string describing exactly when the robot must stop>"
}

Rules:
1. "strategy" must be a non-empty string.
2. "decisions" must be a non-empty list of objects.
3. Every decision object must contain exactly the keys "condition" and "action".
4. "condition" must be a non-empty string.
5. "action" must be one of: FORWARD, LEFT, RIGHT, STOP.
6. "stop_condition" must be a non-empty string.
7. Only use actions that are allowed by the requirement artifact.
8. If "avoid_obstacles" is true, the decisions must handle obstacle avoidance.
9. If "safe_stop" is true, the stop_condition must describe a safe stopping rule.
10. If "avoid_obstacles" is true, the decisions must include at least one
    steering action (LEFT or RIGHT) for obstacle avoidance.
11. If "safe_stop" is true, the decisions must include a STOP action for
    the case when all directions are blocked, AND the stop_condition must
    be explicit (not circular).
12. The plan MUST include GOAL-DIRECTED decisions, not only obstacle
    avoidance. Specifically, the decisions list must explicitly cover:
      - If goal_ahead is true and front_blocked is false, prefer FORWARD.
      - If goal_on_left is true and left_blocked is false, prefer LEFT.
      - If goal_on_right is true and right_blocked is false, prefer RIGHT.
13. Only when no goal direction is safely reachable should the robot fall
    back to obstacle-avoidance steering toward any unblocked direction.
14. If all directions are blocked, the robot must STOP.
15. The decisions list must contain at least one goal-directed decision
    AND at least one obstacle-avoidance fallback decision.
16. The "condition" strings must reference the state field names explicitly
    (e.g. "goal_ahead is true and front_blocked is false") so the
    Developer Agent can translate them directly into Python.
17. The plan MUST also cover the case where a goal direction is blocked
    but other directions are clear. The robot must NOT stop in that case.
    Add fallback decisions such as:
      - If front_blocked is false, prefer FORWARD.
      - If front_blocked is true and left_blocked is false, prefer LEFT.
      - If front_blocked is true and left_blocked is true and right_blocked
        is false, prefer RIGHT.
18. STOP is ONLY allowed when front_blocked, left_blocked, AND right_blocked
    are ALL true. Never STOP if at least one direction is unblocked.
19. The decisions list must be ordered from most specific to most general.
    Goal-directed decisions come first, then generic obstacle-avoidance
    fallbacks, and finally the all-blocked STOP decision.
20. At minimum, the decisions list must include these 7 entries (in order):
      1. goal_ahead is true and front_blocked is false  -> FORWARD
      2. goal_on_left is true and left_blocked is false -> LEFT
      3. goal_on_right is true and right_blocked is false -> RIGHT
      4. front_blocked is false                        -> FORWARD
      5. left_blocked is false                         -> LEFT
      6. right_blocked is false                        -> RIGHT
      7. front_blocked is true and left_blocked is true
         and right_blocked is true                     -> STOP
"""


def validate_plan(data):
    if not isinstance(data, dict):
        raise TypeError("Plan must be a dictionary.")

    required_keys = {"strategy", "decisions", "stop_condition"}
    if set(data.keys()) != required_keys:
        raise ValueError(
            f"Plan must contain exactly the keys {required_keys}, "
            f"got {set(data.keys())}"
        )

    if not isinstance(data["strategy"], str) or not data["strategy"].strip():
        raise ValueError("'strategy' must be a non-empty string.")

    if not isinstance(data["decisions"], list) or not data["decisions"]:
        raise ValueError("'decisions' must be a non-empty list.")

    allowed_actions = {"FORWARD", "LEFT", "RIGHT", "STOP"}
    for i, decision in enumerate(data["decisions"]):
        if not isinstance(decision, dict):
            raise TypeError(f"decisions[{i}] must be a dictionary.")
        if set(decision.keys()) != {"condition", "action"}:
            raise ValueError(
                f"decisions[{i}] must contain exactly 'condition' and 'action'."
            )
        if not isinstance(decision["condition"], str) or not decision["condition"].strip():
            raise ValueError(f"decisions[{i}].condition must be a non-empty string.")
        if decision["action"] not in allowed_actions:
            raise ValueError(
                f"decisions[{i}].action must be one of {allowed_actions}, "
                f"got {decision['action']!r}"
            )

    if not isinstance(data["stop_condition"], str) or not data["stop_condition"].strip():
        raise ValueError("'stop_condition' must be a non-empty string.")

    return data


def run_planner(requirement):
    if not isinstance(requirement, dict):
        raise TypeError("requirement must be a dictionary.")

    user_message = (
        "Here is the validated requirement artifact from the Analyst Agent:\n"
        f"{json.dumps(requirement, indent=2)}\n\n"
        "The robot's state has these boolean fields: "
        "goal_ahead, goal_on_left, goal_on_right, "
        "front_blocked, left_blocked, right_blocked.\n\n"
        "Your plan MUST include:\n"
        "  - goal-directed decisions (move toward the goal when the "
        "corresponding direction is not blocked),\n"
        "  - generic fallback decisions covering the case where a goal "
        "direction is blocked but another direction is clear "
        "(e.g. front_blocked is false -> FORWARD),\n"
        "  - a STOP decision that only fires when ALL three directions "
        "are blocked.\n\n"
        "Never STOP if at least one direction is unblocked.\n\n"
        "Produce the navigation plan JSON now."
    )

    response = chat(
        model="qwen2.5:7b",
        messages=[
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    raw = response["message"]["content"].strip()

    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Planner Agent did not return valid JSON: {e}\nRaw: {raw}")

    return validate_plan(plan)