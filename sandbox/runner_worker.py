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


def _round_trips(value) -> bool:
    """Whether `value` survives the trip home unchanged.

    JSON is the only channel out of this process, and a harvested value is
    written back into a question as `expected`, where it is compared with ==.
    Serialisable is not enough: a tuple encodes fine and comes back a list, and
    (1, 2) != [1, 2] — which would make a correct solution fail its own tests.
    """
    try:
        return json.loads(json.dumps(value)) == value
    except (TypeError, ValueError):
        return False


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
    outputs = []
    passed = 0

    for i, case in enumerate(test_cases):
        try:
            with contextlib.redirect_stdout(captured):
                result = candidate(**case["input"])
        except Exception as e:
            failures.append({"case": i, "reason": f"raised {type(e).__name__}: {e}"})
            outputs.append({"ok": False, "reason": f"raised {type(e).__name__}"})
            continue

        outputs.append(
            {"ok": True, "value": result}
            if _round_trips(result)
            else {"ok": False, "reason": f"{type(result).__name__} is not JSON-stable"}
        )

        # A job with no "expected" is a harvest (sandbox.runner.solution_outputs)
        # rather than a submission: there is nothing to compare against yet, and
        # the caller reads `outputs`.
        if "expected" not in case:
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
        "outputs": outputs,
        "captured_stdout": captured.getvalue(),
    }


def main():
    job = json.loads(sys.stdin.read())
    result = run_job(job)
    print(json.dumps(result))


if __name__ == "__main__":
    main()