# Sandbox

Executes student-submitted code safely against a question's test cases
and produces a `SandboxResult` (defined in `contracts/types.py`).

## How it works

1. **`security.py`** — `check_code_security(code)` statically analyzes
   the submitted code's AST *before any execution*. Blocks dangerous
   imports (`os`, `subprocess`, `socket`, etc.), dangerous builtins
   (`eval`, `exec`, `open`, etc.), and sandbox-escape attribute chains
   (`__subclasses__`, `__globals__`, etc.). Returns `(is_safe, alert)`.
   Raises `SyntaxError` on unparseable code — deliberately not treated
   as a security violation, since broken code isn't malicious code.

2. **`runner.py`** — `run_submission(code, question_id)` is the real
   entry point (wired into `app.py` in place of the old fake stub).
   Runs the security check first; if it fails, returns immediately with
   `status="blocked"` and never executes anything. If it passes, loads
   the question's `test_cases` from `data/questions/`, spawns
   `runner_worker.py` as an isolated subprocess with a timeout, and
   maps the result to `passed`/`failed`/`error`/`timeout`.

3. **`runner_worker.py`** — runs in its own separate process, spawned
   fresh per submission via `subprocess.run()`. This is the only file
   that ever actually executes untrusted code (`exec`/`eval`), and it
   assumes the security check has *already* passed before it's ever
   invoked — it does not re-check.

## Status → SandboxResult mapping

| Status | Meaning | When it happens |
|---|---|---|
| `passed` | All test cases passed | `tests_passed == tests_total > 0` |
| `failed` | At least one test case failed or raised | Normal wrong-answer/bug case |
| `blocked` | Security check rejected the code | Dangerous import/builtin/attribute detected |
| `error` | Code didn't parse, or crashed for a reason unrelated to test correctness | `SyntaxError`, worker crash, unexpected exception |
| `timeout` | Exceeded `TIMEOUT_SECONDS` (currently 5s) | Infinite loop, very slow brute force, etc. |

## Debugging tools

- `sandbox/test_security_manual.py` — sanity-checks `check_code_security`
  against safe code and each blocked category (imports, builtins,
  dunder-escape chains), plus confirms `SyntaxError` propagates
  correctly. Run with `python test_security_manual.py` from `sandbox/`.
- `sandbox/debug_manual.py` — calls `run_submission()` directly,
  bypassing Streamlit entirely, and prints the full `SandboxResult`.
  Much faster than clicking through the UI when debugging; use this
  first if something looks wrong end-to-end.

## Known limitation: stale Streamlit process

If code changes to `sandbox/*.py` don't seem to take effect in the
running app (e.g. a fix that works in `debug_manual.py` doesn't show up
in the browser), Streamlit's autoreloader can miss changes to imported
submodules, especially after file renames. Fully stop (`Ctrl+C`) and
restart (`streamlit run app.py`) rather than relying on the browser
auto-refresh — this bit us once during development.

## Not yet implemented / follow-up ideas

- `TIMEOUT_SECONDS = 5` is a starting guess, not tuned against real
  submission runtimes across question difficulties.
- No memory/resource limit beyond the timeout — a submission that
  allocates huge amounts of memory without looping could still cause
  problems. Worth considering `resource.setrlimit` in the worker if
  this becomes an issue.
- Security check is static-analysis only; it can't catch runtime-only
  attacks that don't appear as syntax patterns. The timeout is the
  main defense against runaway execution, not a full sandbox jail.