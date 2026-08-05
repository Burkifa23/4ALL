"""Synthetic student-log generator.

There is no real user data until Week 13, so the classifier trains on simulated
learning trajectories. Everything here is an explicit, documented parameter and
everything random is seeded: `python -m recommender.simulate` twice produces
byte-identical output.

CALIBRATION AGAINST THE REAL EVALUATOR
--------------------------------------
Score distributions are not invented. They mirror the 15 real gemma2 dumps in
evaluator/testing/sample_evaluations.json:

    efficiency  1:4  2:0  3:3  4:1  5:7      <- never emits 2, and is bimodal
    style       1:0  2:2  3:2  4:7  5:4      <- never emits 1, centred on 4

Two findings drive the design: gemma2 **never emits efficiency 2 or style 1**,
and efficiency is bimodal (brute force -> 1, anything decent -> 5) rather than
bell-shaped. So scores are drawn with np.random.choice over discrete 1-5
weights with those cells pinned to zero, not from a rounded clipped normal
which would have produced a mass of 2s and 3s the real evaluator never gives.

A second realism point taken from app.py: the evaluator only runs on a passing
submission. Failed questions therefore produce no LLM score at all, and the
score features carry over from the last graded attempt.
"""

import collections
import json
from pathlib import Path

import numpy as np
import pandas as pd

from recommender.labeling import label

SEED = 42
N_STUDENTS = 200
SESSION_MIN, SESSION_MAX = 8, 20
MAX_SUBMISSIONS = 4  # a simulated student gives up after this many tries
OUT_PATH = Path("data/synthetic/logs_v1.csv")
QUESTIONS_DIR = Path("data/questions")

# Score weights over [1, 2, 3, 4, 5]. Zeros at eff=2 and style=1 are the
# calibration finding above, not an oversight.
ADVANCED_EFF = [0.03, 0.0, 0.10, 0.20, 0.67]
ADVANCED_STY = [0.0, 0.02, 0.10, 0.43, 0.45]

ARCHETYPES = {
    # pass_prob keyed by difficulty 1/2/3; improvement is added to pass_prob
    # per completed question and also blends scores toward the advanced profile.
    "struggler": {
        "pass_prob": {1: 0.55, 2: 0.25, 3: 0.08},
        "eff": [0.55, 0.0, 0.30, 0.10, 0.05],
        "sty": [0.0, 0.30, 0.40, 0.25, 0.05],
        "improvement": 0.01,
        "jitter": 0.05,
    },
    "average": {
        "pass_prob": {1: 0.80, 2: 0.55, 3: 0.25},
        "eff": [0.20, 0.0, 0.30, 0.20, 0.30],
        "sty": [0.0, 0.10, 0.25, 0.45, 0.20],
        "improvement": 0.02,
        "jitter": 0.05,
    },
    "advanced": {
        "pass_prob": {1: 0.95, 2: 0.85, 3: 0.60},
        "eff": ADVANCED_EFF,
        "sty": ADVANCED_STY,
        "improvement": 0.01,
        "jitter": 0.04,
    },
    "fast_improver": {
        # starts where the struggler starts, climbs six times faster
        "pass_prob": {1: 0.55, 2: 0.25, 3: 0.08},
        "eff": [0.55, 0.0, 0.30, 0.10, 0.05],
        "sty": [0.0, 0.30, 0.40, 0.25, 0.05],
        "improvement": 0.06,
        "jitter": 0.05,
    },
    "inconsistent": {
        # average ability, double the run-to-run noise
        "pass_prob": {1: 0.80, 2: 0.55, 3: 0.25},
        "eff": [0.30, 0.0, 0.20, 0.15, 0.35],
        "sty": [0.0, 0.20, 0.20, 0.35, 0.25],
        "improvement": 0.02,
        "jitter": 0.10,
    },
}

# How fast the score profile shifts toward "advanced" as a student improves.
# fast_improver (0.06) saturates in ~8 questions; struggler (0.01) barely moves.
PROGRESS_GAIN = 2.0


def load_question_index():
    """difficulty -> list of (question_id, topic), from Person 1's real set."""
    index = collections.defaultdict(list)
    for path in sorted(QUESTIONS_DIR.glob("q_*.json")):
        q = json.loads(path.read_text(encoding="utf-8"))
        index[q["difficulty"]].append((q["question_id"], q["topic"]))
    if not index:
        raise FileNotFoundError(
            f"No questions in {QUESTIONS_DIR}. That folder is gitignored — "
            "run the Person 1 ingest first."
        )
    return dict(index)


def _score_weights(params, key, progress):
    """Blend a score profile toward the advanced profile as the student learns."""
    base = np.array(params[key], dtype=float)
    target = np.array(ADVANCED_EFF if key == "eff" else ADVANCED_STY, dtype=float)
    w = (1.0 - progress) * base + progress * target
    return w / w.sum()


def simulate_student(student_id, archetype, rng, index):
    """One student's whole session -> list of row dicts, one per question."""
    params = ARCHETYPES[archetype]
    n_questions = rng.integers(SESSION_MIN, SESSION_MAX + 1)

    difficulty = 1  # placeholder serving policy: everyone starts on Easy
    seen = set()

    session_attempts = 0
    session_passes = 0
    scores = []  # (efficiency, style) of every graded attempt so far

    rows = []
    for position in range(int(n_questions)):
        candidates = [q for q in index.get(difficulty, []) if q[0] not in seen]
        if not candidates:
            break
        qid, topic = candidates[rng.integers(len(candidates))]
        seen.add(qid)

        progress = min(1.0, params["improvement"] * position * PROGRESS_GAIN)
        p = params["pass_prob"][difficulty] + params["improvement"] * position
        p = float(np.clip(p + rng.normal(0, params["jitter"]), 0.02, 0.98))

        # Patience varies per question. Without this every failure would take
        # exactly MAX_SUBMISSIONS tries, handing the model a fake
        # "attempts == 4 means failed" signal no real session would contain.
        patience = int(rng.integers(2, MAX_SUBMISSIONS + 1))
        submissions = 0
        passed = False
        while submissions < patience and not passed:
            submissions += 1
            passed = rng.random() < p

        session_attempts += submissions
        session_passes += int(passed)

        if passed:
            eff = int(rng.choice(5, p=_score_weights(params, "eff", progress)) + 1)
            sty = int(rng.choice(5, p=_score_weights(params, "sty", progress)) + 1)
            scores.append((eff, sty))

        # Feature values as of the moment the recommendation is requested —
        # i.e. after this submission was appended to history. Must match
        # recommender.features.assemble_features exactly.
        if scores:
            avg_eff = sum(s[0] for s in scores) / len(scores)
            avg_sty = sum(s[1] for s in scores) / len(scores)
            last_eff, last_sty = scores[-1]
        else:
            avg_eff = avg_sty = 3.0
            last_eff = last_sty = 3

        user_pass_rate = session_passes / session_attempts

        rows.append(
            {
                "student_id": student_id,
                "archetype": archetype,
                "session_position": position,
                "question_id": qid,
                "question_difficulty": difficulty,
                "question_topic": topic,
                "attempts_on_question": submissions,
                "user_pass_rate": user_pass_rate,
                "avg_efficiency_score": avg_eff,
                "avg_style_score": avg_sty,
                "last_efficiency_score": last_eff,
                "last_style_score": last_sty,
                "label": label(passed, submissions, last_eff if passed else 0, user_pass_rate),
            }
        )

        if rows[-1]["label"] == "level_up":
            difficulty = min(difficulty + 1, 3)

    return rows


def generate(n_students=N_STUDENTS, seed=SEED):
    rng = np.random.default_rng(seed)
    index = load_question_index()
    names = list(ARCHETYPES)

    rows = []
    for i in range(n_students):
        archetype = names[i % len(names)]  # balanced, not sampled
        rows.extend(simulate_student(f"s{i:04d}", archetype, rng, index))
    return pd.DataFrame(rows)


def main():
    df = generate()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)

    counts = df["label"].value_counts()
    print(f"{len(df)} rows from {df.student_id.nunique()} students -> {OUT_PATH}")
    print("\nlabel distribution")
    for name, n in counts.items():
        print(f"  {name:<10} {n:>5}  ({n / len(df):.1%})")
    print("\nlevel_up rate by archetype")
    for arch, sub in df.groupby("archetype"):
        print(f"  {arch:<14} {(sub.label == 'level_up').mean():.1%}")
    print("\nlevel_up rate by session position (fast improvers should climb)")
    fast = df[df.archetype == "fast_improver"]
    early = fast[fast.session_position < 4]
    late = fast[fast.session_position >= 10]
    print(f"  positions 0-3  {(early.label == 'level_up').mean():.1%}")
    print(f"  positions 10+  {(late.label == 'level_up').mean():.1%}")


if __name__ == "__main__":
    main()
