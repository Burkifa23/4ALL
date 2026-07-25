"""
data/ingest/verify_solutions.py

Spot-checks that reference_solution actually executes and passes its own
test_cases for each question file. This does NOT run through any security
sandbox — it's a local, trusted, one-off correctness check on YOUR OWN
generated data, not the untrusted-student-code path (that's a separate,
much more locked-down piece of work).

Usage:
    python verify_solutions.py --dir ../questions
    python verify_solutions.py --dir ../questions --limit 10
"""
import argparse
import json
import sys
from pathlib import Path


def run_one(data: dict) -> list:
    """Return a list of failure strings for this question; empty = all good."""
    failures = []
    namespace = {}

    try:
        exec(data["reference_solution"], namespace)
    except Exception as e:
        return [f"reference_solution failed to exec: {type(e).__name__}: {e}"]

    try:
        candidate = eval(data["entry_point"], namespace)
    except Exception as e:
        return [f"entry_point failed to eval: {type(e).__name__}: {e}"]

    test_cases = data.get("test_cases") or []
    if not test_cases:
        return ["no test_cases to check"]

    for i, case in enumerate(test_cases):
        try:
            result = candidate(**case["input"])
        except Exception as e:
            failures.append(f"case {i} raised {type(e).__name__}: {e}")
            continue
        if result != case["expected"]:
            failures.append(
                f"case {i} mismatch: got {result!r}, expected {case['expected']!r}"
            )

    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", type=Path, default=Path(__file__).parent / "questions")
    parser.add_argument("--limit", type=int, default=None, help="only check the first N files")
    args = parser.parse_args()

    files = sorted(args.dir.glob("q_*.json"))
    if args.limit:
        files = files[: args.limit]

    if not files:
        print(f"No question files found in {args.dir}", file=sys.stderr)
        sys.exit(1)

    total_failures = 0
    for f in files:
        data = json.loads(f.read_text())
        failures = run_one(data)
        if failures:
            total_failures += 1
            print(f"\n{f.name} ({data.get('title')}):")
            for fail in failures[:5]:  # cap noise per file
                print(f"  - {fail}")
            if len(failures) > 5:
                print(f"  ... and {len(failures) - 5} more")

    print(f"\nChecked {len(files)} files, {total_failures} had at least one failure.")


if __name__ == "__main__":
    main()