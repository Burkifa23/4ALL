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
    is single free-function entry points only."""
    starter = row.get("starter_code") or ""
    entry = row.get("entry_point") or ""
    if not entry:
        return False
    if re.search(r"^\s*class\s+\w+", starter, flags=re.MULTILINE):
        return False
    return True


def has_usable_tests(row) -> bool:
    io = row.get("input_output")
    has_io = io is not None and io not in ("", "null")
    starter_ok = has_parseable_code(row.get("starter_code") or "")
    completion_ok = has_parseable_code(
        (row.get("prompt") or "") + (row.get("completion") or "")
    )
    return bool(has_io) and starter_ok and completion_ok


def filter_keep_pile(df: pd.DataFrame) -> pd.DataFrame:
    mask = df.apply(
        lambda r: is_single_function_entry(r) and has_usable_tests(r), axis=1
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
        if isinstance(tags, list):
            topics.update(tags)
    if len(topics) < MIN_TOPICS:
        print(
            f"WARNING: sampled set only covers {len(topics)} topics "
            f"(wanted >= {MIN_TOPICS}). Consider reseeding.",
            file=sys.stderr,
        )
    return sampled


def parse_test_cases(row) -> list:
    """Normalize input_output into [{"input":..., "expected":...}, ...].

    ASSUMPTION (verify against real data, see docs/dataset_notes.md open
    question #1): input_output is a JSON string or dict with parallel
    "inputs" and "outputs" lists. Adjust this function once you see a real row.
    """
    raw = row.get("input_output")
    if raw is None:
        return []
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return []

    if not isinstance(parsed, dict):
        return []
    inputs = parsed.get("inputs", [])
    outputs = parsed.get("outputs", [])
    return [{"input": i, "expected": o} for i, o in zip(inputs, outputs)]


def to_question_record(row, idx: int) -> dict:
    tags = row.get("tags") or []
    if not isinstance(tags, list):
        tags = [tags] if tags else []
    return {
        "question_id": f"q_{idx:04d}",
        "title": (row.get("task_id") or "").replace("-", " ").title(),
        "difficulty": DIFFICULTY_MAP.get(row.get("difficulty"), 0),
        "topic": tags[0] if tags else "misc",
        "topics": tags,
        "description_md": row.get("problem_description", ""),
        "starter_code": row.get("starter_code", ""),
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
    args = parser.parse_args()

    print("Loading newfacade/LeetCodeDataset from Hugging Face...")
    df = load_raw()
    print(f"Loaded {len(df)} total problems across all splits.")

    if args.debug_row is not None:
        print(json.dumps(df.iloc[args.debug_row].to_dict(), indent=2, default=str))
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