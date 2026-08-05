"""
data/ingest/ingest_leetcode.py

Reproducible ingestion pipeline: Hugging Face `newfacade/LeetCodeDataset`
-> cleaned, schema-normalized question JSON files in data/questions/.

Deleting data/questions/ and rerunning this script with the same --seed
must reproduce an identical set of question files (role guide rule #3).

Usage:
    pip install datasets pandas --break-system-packages
    python ingest_leetcode.py --out ../questions

Notes:
  - This was drafted against the dataset's documented schema (see
    docs/dataset_notes.md) without a live connection to verify row shapes.
  - `parse_test_cases()` in particular is a best guess at the inner shape of
    `input_output` — run with --debug-row 0 first and fix the parser against
    real output before trusting a full batch.
"""
import argparse
import ast
import json
import re
import sys
from pathlib import Path

from datasets import load_dataset
import pandas as pd


DIFFICULTY_MAP = {"Easy": 1, "Medium": 2, "Hard": 3}
MIN_TOPICS = 4  # Person 3's feature space wants at least this many distinct tags


def load_raw() -> pd.DataFrame:
    """Load every split of LeetCodeDataset and pool them into one dataframe."""
    ds = load_dataset("newfacade/LeetCodeDataset")
    frames = [ds[split].to_pandas() for split in ds.keys()]
    return pd.concat(frames, ignore_index=True)


def has_parseable_code(code: str) -> bool:
    if not code:
        return False
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def is_single_function_entry(row) -> bool:
    """Reject class-based / design-problem rows (e.g. LRUCache) — keep-pile
    is single free-function entry points only.

    Note: nearly every LeetCodeDataset row wraps its solution in a
    `class Solution:` block, so we can't reject on "contains a class" alone.
    Instead we reject only rows where the class defines more than one
    method — that's the real signal for multi-method design problems.
    """
    starter = row.get("starter_code") or ""
    entry = row.get("entry_point") or ""
    if not entry:
        return False
    method_defs = re.findall(r"^\s{4}def\s+\w+", starter, flags=re.MULTILINE)
    return len(method_defs) <= 1


def _starter_code_parses(code: str) -> bool:
    """starter_code is intentionally left with an empty function body for
    students to fill in, so it will almost never parse standalone. Append
    a synthetic `pass` at one indent level deeper than the last line, just
    to check for real syntax errors (mismatched brackets etc.) without
    penalizing the expected empty body."""
    stripped = code.rstrip()
    if not stripped:
        return False
    last_line = stripped.splitlines()[-1]
    indent = len(last_line) - len(last_line.lstrip(" "))
    candidate = stripped + "\n" + " " * (indent + 4) + "pass\n"
    return has_parseable_code(candidate)

def _finalize_starter_code(starter_code: str) -> str:
    """Make starter_code independently valid, runnable Python — the
    frontend renders this string alone, without the dataset's `prompt`
    boilerplate, so it needs its own typing imports and a real (not
    just internally-checked) function body."""
    stripped = (starter_code or "").rstrip()
    if not stripped:
        return stripped

    last_line = stripped.splitlines()[-1]
    indent = len(last_line) - len(last_line.lstrip(" "))
    body = stripped + "\n" + " " * (indent + 4) + "pass\n"

    return "from typing import *\n\n" + body


def has_usable_tests(row) -> bool:
    io = row.get("input_output")
    if hasattr(io, "tolist"):
        io = io.tolist()
    has_io = io is not None and io not in ("", "null", [])
    starter_ok = _starter_code_parses(row.get("starter_code") or "")
    completion_ok = has_parseable_code(
        (row.get("prompt") or "") + (row.get("completion") or "")
    )
    return bool(has_io) and starter_ok and completion_ok

def uses_tree_or_list_structure(row) -> bool:
    """Tree/linked-list problems (e.g. Binary Tree Paths, Range Sum of BST)
    need object-graph reconstruction via tree_node()/list_node() helpers
    before the reference solution can run — the current flat test_cases
    schema has no way to represent that conversion step. Excluded from the
    v1 keep-pile; see data_note.md for follow-up."""
    starter = row.get("starter_code") or ""
    return bool(re.search(r"\b(TreeNode|ListNode)\b", starter))

def filter_keep_pile(df: pd.DataFrame) -> pd.DataFrame:
    mask = df.apply(
        lambda r: is_single_function_entry(r)
        and has_usable_tests(r)
        and not uses_tree_or_list_structure(r)
        and not uses_external_library(r),
        axis=1,
        
    )
    kept = df[mask].copy()
    return kept


def stratified_sample(
    df: pd.DataFrame, n_easy: int, n_medium: int, n_hard: int, seed: int
) -> pd.DataFrame:
    parts = []
    for difficulty, n in [("Easy", n_easy), ("Medium", n_medium), ("Hard", n_hard)]:
        pool = df[df["difficulty"] == difficulty]
        if len(pool) < n:
            print(
                f"WARNING: only {len(pool)} usable '{difficulty}' problems, "
                f"wanted {n}. Taking all available.",
                file=sys.stderr,
            )
            n = len(pool)
        parts.append(pool.sample(n=n, random_state=seed))
    sampled = pd.concat(parts, ignore_index=True)

    topics = set()
    for tags in sampled["tags"]:
            topics.update(parse_tags(tags))
    if len(topics) < MIN_TOPICS:
        print(
            f"WARNING: sampled set only covers {len(topics)} topics "
            f"(wanted >= {MIN_TOPICS}). Consider reseeding.",
            file=sys.stderr,
        )
    return sampled


def _parse_kwargs(input_str: str) -> dict:
    """Turn 'nums = [3,3], target = 6' into {'nums': [3, 3], 'target': 6}
    by parsing it as if it were a keyword-argument call, then reading the
    AST directly (no eval() of untrusted content)."""
    tree = ast.parse(f"f({input_str})", mode="eval")
    return {kw.arg: ast.literal_eval(kw.value) for kw in tree.body.keywords}

def _parse_expected(output_str: str, return_type_hint: str = ""):
    if return_type_hint == "str":
        return output_str
    if return_type_hint == "bool":
        if output_str in ("true", "True"):
            return True
        if output_str in ("false", "False"):
            return False
    try:
        return ast.literal_eval(output_str)
    except (ValueError, SyntaxError):
        return output_str

def _return_type_hint(starter_code: str) -> str:
    match = re.search(r"->\s*([\w\[\], ]+):", starter_code or "")
    return match.group(1).strip() if match else ""

_ALLOWED_IMPORTS = {
    "typing", "functools", "collections", "itertools", "heapq", "bisect",
    "string", "operator", "math", "random", "datetime", "re", "sys",
}


def uses_external_library(row) -> bool:
    """Reference solutions that import third-party packages (e.g.
    sortedcontainers) can't run in a sandbox restricted to stdlib —
    excluded from v1 keep-pile, see data_note.md."""
    code = (row.get("prompt") or "") + (row.get("completion") or "")
    imports = re.findall(r"^\s*(?:import|from)\s+([\w.]+)", code, flags=re.MULTILINE)
    return any(imp.split(".")[0] not in _ALLOWED_IMPORTS for imp in imports)

_ERROR_OUTPUT_PREFIXES = (
    "Error:",
    "Execution timed out",
    "Exception:",
    "Traceback",
)


def _is_error_capture(output_str) -> bool:
    """Some rows record an execution error or timeout from a broken
    auto-generated case instead of a real expected value — there's no
    sound way to test against 'the code should time out'. Skip these."""
    return isinstance(output_str, str) and output_str.startswith(_ERROR_OUTPUT_PREFIXES)


def parse_test_cases(row) -> list:
    raw = row.get("input_output")
    if raw is None:
        return []

    if hasattr(raw, "tolist"):
        raw = raw.tolist()

    if isinstance(raw, str):
        fixed = re.sub(r"}\s*\n\s*{", "}, {", raw)
        try:
            raw = ast.literal_eval(fixed)
        except (ValueError, SyntaxError):
            return []

    if not isinstance(raw, (list, tuple)):
        return []

    return_hint = _return_type_hint(row.get("starter_code") or "")
    cases = []
    for item in raw:
        output_str = item.get("output", "")
        # Some rows capture an execution error from a broken auto-generated
        # case (e.g. mismatched indices) instead of a real expected value.
        # There's no sound way to test against "should raise this exact
        # error string" — skip these.
        
        if _is_error_capture(output_str):
            continue
        try:
            args = _parse_kwargs(item.get("input", ""))
            expected = _parse_expected(output_str, return_hint)
        except (ValueError, SyntaxError, AttributeError):
            continue
        cases.append({"input": args, "expected": expected})
    return cases


def parse_tags(tags_raw) -> list:
    """Normalize the dataset's `tags` field into a clean list of strings.

    After `.to_pandas()`, a HF Sequence(string) column comes through as a
    numpy array, not a Python list or string — so a plain truthiness check
    (`if not tags_raw`) is ambiguous and raises on multi-element arrays.
    Handle array-like, plain list, and string forms defensively.
    """
    if tags_raw is None:
        return []
    if hasattr(tags_raw, "tolist"):  # numpy array / pandas Series
        return list(tags_raw.tolist())
    if isinstance(tags_raw, (list, tuple)):
        return list(tags_raw)
    if isinstance(tags_raw, str):
        return re.findall(r"'([^']*)'", tags_raw)
    return []


def to_question_record(row, idx: int) -> dict:
    tags = parse_tags(row.get("tags"))
    return {
        "question_id": f"q_{idx:04d}",
        "title": (row.get("task_id") or "").replace("-", " ").title(),
        "difficulty": DIFFICULTY_MAP.get(row.get("difficulty"), 0),
        "topic": tags[0] if tags else "misc",
        "topics": tags,
        "description_md": row.get("problem_description", ""),
        "starter_code": _finalize_starter_code(row.get("starter_code")),
        "entry_point": row.get("entry_point", ""),
        "reference_solution": (row.get("prompt") or "") + (row.get("completion") or ""),
        "test_cases": parse_test_cases(row),
        "test_case_count": len(parse_test_cases(row)),
        "optimal_complexity": None,  # filled in a manual labeling pass later
        "source_task_id": row.get("task_id"),
        "source_question_id": row.get("question_id"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-easy", type=int, default=20)
    parser.add_argument("--n-medium", type=int, default=20)
    parser.add_argument("--n-hard", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).parent.parent / "questions"
    )
    parser.add_argument(
        "--debug-row",
        type=int,
        default=None,
        help="Print the raw dict for this row index of the RAW (pre-filter) "
        "dataframe and exit. Use this first to check real field shapes.",
    )
    parser.add_argument("--debug-task-id", type=str, default=None)
    args = parser.parse_args()

    print("Loading newfacade/LeetCodeDataset from Hugging Face...")
    df = load_raw()
    print(f"Loaded {len(df)} total problems across all splits.")

    if args.debug_row is not None:
        row = df.iloc[args.debug_row]
        print(json.dumps(row.to_dict(), indent=2, default=str))
        print("\n--- PARSED ---")
        print("tags:", parse_tags(row.get("tags")))
        print("is_single_function_entry:", is_single_function_entry(row))
        print("test_cases[0]:", parse_test_cases(row)[0] if parse_test_cases(row) else "EMPTY")
        return
    elif args.debug_task_id is not None:
        matches = df[df["task_id"] == args.debug_task_id]
        if matches.empty:
            print(f"No row found with task_id={args.debug_task_id!r}", file=sys.stderr)
            return
        row = matches.iloc[0]
        print("input_output (raw):")
        print(row.get("input_output"))
        print("\nparsed test_cases:", parse_test_cases(row))
        print("has_usable_tests:", has_usable_tests(row))
        return
    keep = filter_keep_pile(df)
    print(
        f"Keep-pile after filtering: {len(keep)} problems "
        f"({len(df) - len(keep)} discarded as unusable)."
    )

    wanted = args.n_easy + args.n_medium + args.n_hard
    if len(keep) < wanted:
        print(
            "ESCALATE: keep-pile is smaller than the requested sample size. "
            "Flag to the team before proceeding (role guide Day 1 trigger).",
            file=sys.stderr,
        )

    sampled = stratified_sample(keep, args.n_easy, args.n_medium, args.n_hard, args.seed)

    args.out.mkdir(parents=True, exist_ok=True)
    for i, (_, row) in enumerate(sampled.iterrows(), start=1):
        record = to_question_record(row, i)
        out_path = args.out / f"{record['question_id']}.json"
        out_path.write_text(json.dumps(record, indent=2))

    print(f"Wrote {len(sampled)} question files to {args.out}")


if __name__ == "__main__":
    main()