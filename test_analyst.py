import json, os
from analyst_agent import run_analyst, validate_requirements

BRIEF = "brief.txt"
OUT = os.path.join("artifacts", "requirements.json")

def test_analyst_pipeline():
    with open(BRIEF, encoding="utf-8") as f:
        brief = f.read()

    req = run_analyst(brief)
    validate_requirements(req)

    os.makedirs("artifacts", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(req, f, ensure_ascii=False, indent=2)

    print(json.dumps(req, ensure_ascii=False, indent=2))
    assert isinstance(req, dict)
    assert "goal" in req