"""
sandbox/test_security_manual.py

Quick manual sanity check for check_code_security() before building the
subprocess runner on top of it. Not a full test suite — just enough to
confirm safe code passes, each blocked category is actually caught, and
syntax errors propagate correctly rather than being swallowed.

Usage:
    python test_security_manual.py
"""
from security import check_code_security

CASES = [
    ("safe_basic", """
def solution(nums, target):
    d = {}
    for i, x in enumerate(nums):
        if target - x in d:
            return [d[target - x], i]
        d[x] = i
""", True),

    ("safe_common_imports", """
import re
import random
from collections import defaultdict

def solution(s):
    return re.sub(r"[aeiou]", "", s)
""", True),

    ("blocked_os_import", """
import os

def solution():
    return os.listdir(".")
""", False),

    ("blocked_subprocess_import", """
import subprocess

def solution():
    return subprocess.run(["ls"])
""", False),

    ("blocked_from_import", """
from os import system

def solution():
    return system("whoami")
""", False),

    ("blocked_eval", """
def solution(expr):
    return eval(expr)
""", False),

    ("blocked_open", """
def solution():
    with open("/etc/passwd") as f:
        return f.read()
""", False),

    ("blocked_dunder_escape", """
def solution():
    base = ().__class__.__bases__[0]
    return base.__subclasses__()
""", False),

    ("blocked_import_aliased", """
import os as o

def solution():
    return o.getcwd()
""", False),
]

SYNTAX_ERROR_CASE = """
def solution(:
    return 1
"""


def run():
    passed = 0
    failed = 0

    for name, code, expected_safe in CASES:
        try:
            is_safe, alert = check_code_security(code)
        except SyntaxError as e:
            print(f"[UNEXPECTED] {name}: raised SyntaxError ({e}) — this case shouldn't have one")
            failed += 1
            continue

        ok = is_safe == expected_safe
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: is_safe={is_safe} alert={alert!r}")
        if ok:
            passed += 1
        else:
            failed += 1

    # Separately confirm syntax errors propagate rather than getting
    # silently treated as "safe" or "blocked".
    try:
        check_code_security(SYNTAX_ERROR_CASE)
        print("[FAIL] syntax_error_case: expected SyntaxError, none raised")
        failed += 1
    except SyntaxError:
        print("[PASS] syntax_error_case: SyntaxError correctly propagated")
        passed += 1

    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")


if __name__ == "__main__":
    run()