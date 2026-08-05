"""Week 13 evaluation: model vs humans, rules baseline vs humans.

Two steps, run a week apart.

    python -m recommender.evaluate --sample 15
        Samples decisions from data/predictions.jsonl and writes a blank
        rating sheet. Give a copy to each rater.

    python -m recommender.evaluate
        Reads every data/evaluation/ratings_*.csv, majority-votes them into
        ground truth, and reports agreement for both the model and the rules
        baseline, plus the disagreement cases for the report.

The rating sheet deliberately does NOT show the model's decision. Raters who
can see the answer stop being an independent baseline.
"""

import argparse
import collections
import csv
import json
import random
import tempfile
from pathlib import Path

from contracts.types import FeatureVector
from recommender import engine

EVAL_DIR = Path("data/evaluation")
CASES_PATH = EVAL_DIR / "cases.json"
SHEET_PATH = EVAL_DIR / "rating_sheet.csv"
PREDICTIONS = Path("data/predictions.jsonl")

# Recomputing the rules baseline must not append to the prediction log we are
# in the middle of evaluating.
engine.PREDICTION_LOG = Path(tempfile.gettempdir()) / "recommender_evaluate.jsonl"

SHEET_FIELDS = [
    "case_id",
    "question_difficulty",
    "attempts_on_question",
    "user_pass_rate",
    "avg_efficiency_score",
    "last_efficiency_score",
    "last_style_score",
    "decision",  # rater fills this in: reinforce | level_up
]


def load_predictions():
    if not PREDICTIONS.exists():
        raise SystemExit(
            f"{PREDICTIONS} not found. It is written by recommend_next() during "
            "live sessions — run the app first."
        )
    with PREDICTIONS.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def sample(n, seed=42):
    """Write a blank rating sheet plus the hidden answer key."""
    records = [r for r in load_predictions() if r["mode"] == "model"]
    if len(records) < n:
        print(f"warning: only {len(records)} model decisions logged, wanted {n}")
        n = len(records)

    chosen = random.Random(seed).sample(records, n)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    cases = []
    with SHEET_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SHEET_FIELDS)
        writer.writeheader()
        for i, record in enumerate(chosen):
            case_id = f"c{i:02d}"
            cases.append({"case_id": case_id, **record})
            row = {k: record["vector"].get(k, "") for k in SHEET_FIELDS}
            row["case_id"] = case_id
            row["decision"] = ""
            writer.writerow(row)

    CASES_PATH.write_text(json.dumps(cases, indent=2), encoding="utf-8")
    print(f"wrote {SHEET_PATH} ({n} cases) and {CASES_PATH}")
    print("Each rater: copy the sheet to ratings_<name>.csv, fill the decision "
          "column with 'reinforce' or 'level_up', save it in data/evaluation/.")


def majority(decisions):
    """Most-voted decision; ties resolve to reinforce (the conservative action)."""
    counts = collections.Counter(decisions)
    top = counts.most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        return "reinforce"
    return top[0][0]


def load_ratings():
    """case_id -> list of rater decisions, from data/evaluation/ratings_*.csv."""
    sheets = sorted(EVAL_DIR.glob("ratings_*.csv"))
    if not sheets:
        raise SystemExit(
            f"No ratings_*.csv in {EVAL_DIR}. Run --sample first, then have each "
            "rater fill in a copy."
        )
    ratings = collections.defaultdict(list)
    for sheet in sheets:
        with sheet.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                decision = (row.get("decision") or "").strip()
                if decision:
                    ratings[row["case_id"]].append(decision)
    print(f"{len(sheets)} rater sheets: {', '.join(s.stem for s in sheets)}")
    return ratings


def _vector(record):
    return FeatureVector(**record["vector"])


def report():
    cases = {c["case_id"]: c for c in json.loads(CASES_PATH.read_text(encoding="utf-8"))}
    ratings = load_ratings()

    rows = []
    for case_id, decisions in sorted(ratings.items()):
        case = cases[case_id]
        rows.append(
            {
                "case_id": case_id,
                "human": majority(decisions),
                "votes": collections.Counter(decisions),
                "model": case["decision"],
                "confidence": case["confidence"],
                "rules": engine.rules_baseline(_vector(case)).decision,
                "vector": case["vector"],
            }
        )

    n = len(rows)
    model_agree = sum(r["model"] == r["human"] for r in rows)
    rules_agree = sum(r["rules"] == r["human"] for r in rows)
    unanimous = sum(len(set(ratings[r["case_id"]])) == 1 for r in rows)

    print(f"\n=== agreement with human majority (n={n}) ===")
    print(f"  decision tree   {model_agree}/{n}  ({model_agree / n:.1%})")
    print(f"  rules baseline  {rules_agree}/{n}  ({rules_agree / n:.1%})")
    print(f"  raters unanimous on {unanimous}/{n} cases ({unanimous / n:.1%})")

    print("\n=== per-class (human label as ground truth) ===")
    for cls in ("level_up", "reinforce"):
        subset = [r for r in rows if r["human"] == cls]
        if not subset:
            continue
        m = sum(r["model"] == cls for r in subset)
        b = sum(r["rules"] == cls for r in subset)
        print(f"  {cls:<10} n={len(subset):<3} tree recall {m / len(subset):.1%}  "
              f"rules recall {b / len(subset):.1%}")

    disagreements = [r for r in rows if r["model"] != r["human"]]
    print(f"\n=== disagreement cases ({len(disagreements)}) ===")
    for r in disagreements:
        v = r["vector"]
        print(f"\n  {r['case_id']}: humans {r['human']} ({dict(r['votes'])}), "
              f"model {r['model']} (confidence {r['confidence']:.2f}), "
              f"rules {r['rules']}")
        print(f"    difficulty {v['question_difficulty']}, "
              f"attempts {v['attempts_on_question']}, "
              f"pass rate {v['user_pass_rate']:.2f}, "
              f"last efficiency {v['last_efficiency_score']}, "
              f"last style {v['last_style_score']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, metavar="N",
                        help="write a blank rating sheet with N cases")
    args = parser.parse_args()
    if args.sample:
        sample(args.sample)
    else:
        report()


if __name__ == "__main__":
    main()
