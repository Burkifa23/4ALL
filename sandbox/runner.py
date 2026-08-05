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


def _load_question(question_id) -> dict:
    if not _question_cache:
        for f in QUESTIONS_DIR.glob("q_*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            _question_cache[data["question_id"]] = data
    if question_id not in _question_cache:
        raise ValueError(f"No question found with question_id={question_id!r}")
    return _question_cache[question_id]


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
        return SandboxResult(
            status="timeout",
            tests_passed=0,
            tests_total=len(job["test_cases"]),
            failed_case_summary=f"Exceeded {TIMEOUT_SECONDS}s time limit",
            security_alert=None,
            stdout="",
            runtime_ms=runtime_ms,
        )
    runtime_ms = int((time.monotonic() - start) * 1000)

    if proc.returncode != 0:
        return SandboxResult(
            status="error",
            tests_passed=0,
            tests_total=len(job["test_cases"]),
            failed_case_summary=f"Worker process crashed: {proc.stderr.strip()[:500]}",
            security_alert=None,
            stdout="",
            runtime_ms=runtime_ms,
        )

    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return SandboxResult(
            status="error",
            tests_passed=0,
            tests_total=len(job["test_cases"]),
            failed_case_summary="Worker produced invalid output",
            security_alert=None,
            stdout=proc.stdout[:500],
            runtime_ms=runtime_ms,
        )

    if result.get("crashed"):
        return SandboxResult(
            status="error",
            tests_passed=0,
            tests_total=len(job["test_cases"]),
            failed_case_summary=result.get("error", "Unknown error"),
            security_alert=None,
            stdout=result.get("captured_stdout", ""),
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