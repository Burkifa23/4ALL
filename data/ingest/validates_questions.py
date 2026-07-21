"""
data/validate_questions.py

Machine-validates every JSON file in data/questions/ against the schema
documented in data/README.md. Run after every ingest, before committing.

Usage:
    python validate_questions.py
    python validate_questions.py --dir ./questions
"""
import argparse
import ast
import json
import sys
from pathlib import Path

REQUIRED_FIELDS = {
    "question_id", "title", "difficulty", "topic", "topics",
    "description_md", "starter_code", "entry_point",
    "reference_solution", "test_cases", "test_case_count",
    "optimal_complexity", "source_task_id", "source_question_id",
}

VALID_DIFFICULTIES = {0, 1, 2, 3}


def validate_file(path: Path) -> list:
    """Return a list of error strings; empty list means the file is clean."""
    errors = []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [f"{path.name}: invalid JSON ({e})"]

    missing = REQUIRED_FIELDS - data.keys()
    if missing:
        errors.append(f"{path.name}: missing fields {sorted(missing)}")

    if data.get("difficulty") not in VALID_DIFFICULTIES:
        errors.append(f"{path.name}: bad difficulty value {data.get('difficulty')!r}")

    if not data.get("entry_point"):
        errors.append(f"{path.name}: empty entry_point")

    starter = data.get("starter_code", "")
    try:
        ast.parse(starter)
    except SyntaxError as e:
        errors.append(f"{path.name}: starter_code does not parse ({e})")

    solution = data.get("reference_solution", "")
    try:
        ast.parse(solution)
    except SyntaxError as e:
        errors.append(f"{path.name}: reference_solution does not parse ({e})")

    tests = data.get("test_cases") or []
    if len(tests) == 0:
        errors.append(f"{path.name}: zero test cases")

    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=Path, default=Path(__file__).parent / "questions")
    args = parser.parse_args()

    files = sorted(args.dir.glob("q_*.json"))
    if not files:
        print(f"No question files found in {args.dir}", file=sys.stderr)
        sys.exit(1)

    ids_seen = set()
    all_errors = []
    for f in files:
        all_errors.extend(validate_file(f))
        data = json.loads(f.read_text())
        qid = data.get("question_id")
        if qid in ids_seen:
            all_errors.append(f"{f.name}: duplicate question_id {qid}")
        ids_seen.add(qid)

    print(f"Checked {len(files)} question files.")
    if all_errors:
        print(f"\n{len(all_errors)} error(s) found:\n")
        for e in all_errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("All files valid. [✓]")


if __name__ == "__main__":
    main()