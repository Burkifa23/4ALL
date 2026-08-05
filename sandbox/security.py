"""
sandbox/security.py

AST-based security check for student-submitted code, run BEFORE any
execution. This never executes the submitted code — it only inspects
its parsed syntax tree. If this check fails, the code must never be
run at all (status="blocked" in SandboxResult).

Policy: "looser" blocklist — block only imports and operations that
give direct system/process/network access or let code escape the
sandbox via introspection tricks. Other imports (random, re, json,
hashlib, itertools, etc.) are allowed.
"""
import ast

# Modules that give direct OS/process/network/filesystem access.
BLOCKED_MODULES = {
    "os", "subprocess", "socket", "sys", "shutil", "ctypes",
    "multiprocessing", "threading", "signal", "pty", "fcntl",
    "resource", "importlib", "pickle", "marshal", "code", "pdb",
}

# Builtins that can execute arbitrary code, read/write files, or
# inspect/modify the running interpreter's state.
BLOCKED_BUILTINS = {
    "eval", "exec", "compile", "__import__", "open", "input",
    "globals", "locals", "vars", "breakpoint", "exit", "quit",
    "help", "memoryview",
}

# Dunder attributes commonly used in sandbox-escape chains, e.g.
# ().__class__.__bases__[0].__subclasses__() to reach dangerous
# classes without ever writing "import os" or "import subprocess".
BLOCKED_DUNDER_ATTRS = {
    "__subclasses__", "__globals__", "__builtins__", "__base__",
    "__bases__", "__mro__", "__getattribute__", "__reduce__",
    "__reduce_ex__", "__import__",
}


class SecurityViolation:
    def __init__(self, message: str, line: int):
        self.message = message
        self.line = line

    def __str__(self):
        return f"Line {self.line}: {self.message}"


def _root_module_name(node) -> str:
    """For 'import a.b.c' or 'from a.b.c import x', return 'a'."""
    return (node.module or "").split(".")[0] if isinstance(node, ast.ImportFrom) else ""


def check_code_security(code: str):
    """
    Statically analyze submitted code for dangerous operations.

    Returns (is_safe: bool, security_alert: str | None).

    Raises SyntaxError if `code` doesn't parse — the caller should catch
    this separately and treat it as status="error" (a syntax error isn't
    a security violation, just broken code).
    """
    tree = ast.parse(code)  # let SyntaxError propagate to the caller
    violations = []

    for node in ast.walk(tree):
        # --- import ... / import ...as / from ... import ... ---
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in BLOCKED_MODULES:
                    violations.append(
                        SecurityViolation(f"blocked import '{alias.name}'", node.lineno)
                    )
        elif isinstance(node, ast.ImportFrom):
            root = _root_module_name(node)
            if root in BLOCKED_MODULES:
                violations.append(
                    SecurityViolation(f"blocked import 'from {node.module}'", node.lineno)
                )

        # --- calls to dangerous builtins, e.g. eval(...), open(...) ---
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in BLOCKED_BUILTINS:
                violations.append(
                    SecurityViolation(f"blocked call to '{func.id}()'", node.lineno)
                )

        # --- dunder attribute access used in sandbox-escape chains ---
        elif isinstance(node, ast.Attribute):
            if node.attr in BLOCKED_DUNDER_ATTRS:
                violations.append(
                    SecurityViolation(f"blocked attribute access '.{node.attr}'", node.lineno)
                )

    if violations:
        # Report the first violation; keep it short and clear for the
        # student rather than dumping every match found.
        first = violations[0]
        suffix = f" (+{len(violations) - 1} more)" if len(violations) > 1 else ""
        return False, f"{first}{suffix}"

    return True, None