"""
sandbox/runner_worker.py

Runs in its own, separate Python process. Reads a JSON job from stdin:
    {"code": "...", "entry_point": "...", "test_cases": [...]}
Executes the submitted code against each test case and writes a JSON
result to stdout:
    {"tests_passed": N, "tests_total": M, "failures": [...], "captured_stdout": "..."}

This script assumes the code has ALREADY passed the AST security check
(sandbox/security.py) before this process was ever spawned — it does not
re-check. Never invoke this worker on code that hasn't been vetted.
"""
import contextlib
import io
import json
import sys


def run_job(job: dict) -> dict:
    namespace = {}
    captured = io.StringIO()

    try:
        with contextlib.redirect_stdout(captured):
            exec(job["code"], namespace)
    except Exception as e:
        return {
            "crashed": True,
            "error": f"{type(e).__name__}: {e}",
            "captured_stdout": captured.getvalue(),
        }

    try:
        with contextlib.redirect_stdout(captured):
            candidate = eval(job["entry_point"], namespace)
    except Exception as e:
        return {
            "crashed": True,
            "error": f"entry_point failed to eval: {type(e).__name__}: {e}",
            "captured_stdout": captured.getvalue(),
        }

    test_cases = job.get("test_cases", [])
    failures = []
    passed = 0

    for i, case in enumerate(test_cases):
        try:
            with contextlib.redirect_stdout(captured):
                result = candidate(**case["input"])
        except Exception as e:
            failures.append({"case": i, "reason": f"raised {type(e).__name__}: {e}"})
            continue
        if result == case["expected"]:
            passed += 1
        else:
            failures.append({
                "case": i,
                "reason": f"got {result!r}, expected {case['expected']!r}",
            })

    return {
        "crashed": False,
        "tests_passed": passed,
        "tests_total": len(test_cases),
        "failures": failures,
        "captured_stdout": captured.getvalue(),
    }


def main():
    job = json.loads(sys.stdin.read())
    result = run_job(job)
    print(json.dumps(result))


if __name__ == "__main__":
    main()