"""
sandbox/debug_manual.py

Direct call into run_submission(), bypassing Streamlit entirely, to see
the FULL SandboxResult (including security_alert / failed_case_summary)
that the UI currently hides for non-passed/failed statuses.

Usage:
    cd sandbox
    python debug_manual.py
"""
import sys
from pathlib import Path

# Make sure the project root is importable, same as when run via streamlit.
sys.path.insert(0, str(Path(__file__).parent.parent))

from sandbox.runner import run_submission

CODE = """
import os
def solution():
    return os.listdir(".")
"""

result = run_submission(CODE, 1)  # question_id=1, adjust if needed

print("status:", result.status)
print("tests_passed:", result.tests_passed)
print("tests_total:", result.tests_total)
print("failed_case_summary:", result.failed_case_summary)
print("security_alert:", result.security_alert)
print("stdout:", result.stdout)
print("runtime_ms:", result.runtime_ms)