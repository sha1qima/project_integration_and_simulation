import importlib.util
import os
import pytest

def load_module():
    spec = importlib.util.spec_from_file_location("navigation_logic", os.path.join(os.path.dirname(__file__), "artifacts", "navigation_logic.py"))
    navigation_logic = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(navigation_logic)
    return navigation_logic.decide_next_move

decide_next_move = load_module()

@pytest.mark.parametrize("state, expected", [
    ({"goal_ahead": True, "front_blocked": False}, "FORWARD"),
    ({"goal_on_left": True, "left_blocked": False}, "LEFT"),
    ({"goal_on_right": True, "right_blocked": False}, "RIGHT"),
    ({"front_blocked": False, "left_blocked": True, "right_blocked": True}, "FORWARD"),
    ({"front_blocked": True, "left_blocked": False, "right_blocked": True}, "LEFT"),
    ({"front_blocked": True, "left_blocked": True, "right_blocked": False}, "RIGHT"),
    ({"front_blocked": True, "left_blocked": True, "right_blocked": True}, "STOP"),
])
def test_decide_next_move(state, expected):
    assert decide_next_move(state) in {"FORWARD", "LEFT", "RIGHT", "STOP"} and decide_next_move(state) == expected