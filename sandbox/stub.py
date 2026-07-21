from contracts.types import SandboxResult


def run_submission(code, question_id):

    # fake behavior for testing

    if "print" in code:
        return SandboxResult(
            status="passed",
            tests_passed=5,
            tests_total=5,
            failed_case_summary=None,
            security_alert=None,
            stdout="Correct output",
            runtime_ms=120,
        )

    else:
        return SandboxResult(
            status="failed",
            tests_passed=2,
            tests_total=5,
            failed_case_summary="Expected 10 but got 5",
            security_alert=None,
            stdout="",
            runtime_ms=150,
        )
