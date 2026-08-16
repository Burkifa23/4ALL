"""
sandbox/runner.py

Real implementation of run_submission(), replacing sandbox/stub.py.
Runs the AST security check first, then spawns runner_worker.py in an
isolated subprocess with a timeout to actually execute the candidate
code against the question's test cases.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

from contracts.types import SandboxResult
from sandbox.security import check_code_security

TIMEOUT_SECONDS = 5
QUESTIONS_DIR = Path(__file__).parent.parent / "data" / "questions"
WORKER_SCRIPT = Path(__file__).parent / "runner_worker.py"

_question_cache = {}


def _prime_cache() -> None:
    if not _question_cache:
        for f in QUESTIONS_DIR.glob("q_*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            _question_cache[data["question_id"]] = data


def register_question(record: dict) -> None:
    """Make a question runnable that was never written to data/questions/.

    Generated questions (evaluator/generate.py) live only in memory and in
    data/generated/. Priming first is not optional: an empty cache is the
    "not loaded yet" signal, so registering into it before the disk pass would
    make every real question disappear.
    """
    _prime_cache()
    _question_cache[record["question_id"]] = record


def _load_question(question_id) -> dict:
    _prime_cache()
    if question_id not in _question_cache:
        raise ValueError(f"No question found with question_id={question_id!r}")
    return _question_cache[question_id]


def _run_worker(job: dict):
    """Spawn the worker on `job`. Returns (result, failure, runtime_ms), where
    exactly one of result/failure is None and failure is (status, summary,
    stdout) — everything the caller needs to describe what went wrong.

    Shared by run_submission() and solution_outputs() so the timeout, the crash
    handling and the "worker answered with garbage" case have one definition
    each. Callers are responsible for the security check BEFORE calling this;
    the worker does not re-check.
    """
    start = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, str(WORKER_SCRIPT)],
            input=json.dumps(job),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        runtime_ms = int((time.monotonic() - start) * 1000)
        return None, ("timeout", f"Exceeded {TIMEOUT_SECONDS}s time limit", ""), runtime_ms

    runtime_ms = int((time.monotonic() - start) * 1000)

    if proc.returncode != 0:
        summary = f"Worker process crashed: {proc.stderr.strip()[:500]}"
        return None, ("error", summary, ""), runtime_ms

    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        failure = ("error", "Worker produced invalid output", proc.stdout[:500])
        return None, failure, runtime_ms

    if result.get("crashed"):
        summary = result.get("error", "Unknown error")
        return None, ("error", summary, result.get("captured_stdout", "")), runtime_ms

    return result, None, runtime_ms


def solution_outputs(record: dict) -> list:
    """What record["reference_solution"] really returns for each test input.

    One {"ok": True, "value": ...} or {"ok": False, "reason": ...} per test
    case, in order; [] if the solution never ran at all.

    This exists because the generator model cannot predict its own code's
    output — measured at 0/20 on held-out topics, see
    docs/codegen_tutor_findings.md — so evaluator/generate.py computes the
    expected values rather than trusting the ones the model wrote. Same AST
    security check and same isolated subprocess as a student submission: this
    is model-written code and gets no more trust than any other.
    """
    code = record["reference_solution"]

    try:
        is_safe, _ = check_code_security(code)
    except SyntaxError:
        return []

    if not is_safe:
        return []

    result, failure, _ = _run_worker({
        "code": code,
        "entry_point": record["entry_point"],
        "test_cases": record["test_cases"],
    })

    return [] if failure is not None else result.get("outputs", [])


def run_submission(code: str, question_id) -> SandboxResult:
    # --- 1. Security check, before anything is ever executed ---
    try:
        is_safe, security_alert = check_code_security(code)
    except SyntaxError as e:
        return SandboxResult(
            status="error",
            tests_passed=0,
            tests_total=0,
            failed_case_summary=f"Code does not parse: {e}",
            security_alert=None,
            stdout="",
            runtime_ms=0,
        )

    if not is_safe:
        return SandboxResult(
            status="blocked",
            tests_passed=0,
            tests_total=0,
            failed_case_summary=None,
            security_alert=security_alert,
            stdout="",
            runtime_ms=0,
        )

    # --- 2. Load question data ---
    question = _load_question(question_id)
    job = {
        "code": code,
        "entry_point": question["entry_point"],
        "test_cases": question["test_cases"],
    }

    # --- 3. Run in an isolated subprocess with a timeout ---
    result, failure, runtime_ms = _run_worker(job)

    if failure is not None:
        status, summary, stdout = failure
        return SandboxResult(
            status=status,
            tests_passed=0,
            tests_total=len(job["test_cases"]),
            failed_case_summary=summary,
            security_alert=None,
            stdout=stdout,
            runtime_ms=runtime_ms,
        )

    tests_passed = result["tests_passed"]
    tests_total = result["tests_total"]
    failures = result["failures"]

    if tests_passed == tests_total and tests_total > 0:
        status = "passed"
        failed_case_summary = None
    else:
        status = "failed"
        failed_case_summary = failures[0]["reason"] if failures else "No test cases ran"

    return SandboxResult(
        status=status,
        tests_passed=tests_passed,
        tests_total=tests_total,
        failed_case_summary=failed_case_summary,
        security_alert=None,
        stdout=result.get("captured_stdout", ""),
        runtime_ms=runtime_ms,
    )