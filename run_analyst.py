import json
import os
from analyst_agent import run_analyst


BRIEF_PATH = "brief.txt"
OUTPUT_PATH = os.path.join("artifacts", "requirements.json")


def load_brief(path=BRIEF_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def save_requirements(requirements, path=OUTPUT_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(requirements, f, ensure_ascii=False, indent=2)


def main():
    brief_text = load_brief()
    requirements = run_analyst(brief_text)   # 已经过 validate_requirements
    save_requirements(requirements)
    print("[OK] saved to %s" % OUTPUT_PATH)
    print(json.dumps(requirements, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()