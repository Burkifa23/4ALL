"""Turn session transcripts into one observation row per participant.

Everything a log can answer, a log should answer. A note-taker running a
25-minute session cannot both capture verbatim confusions and tally attempts,
and the tallies are the half that is recoverable afterwards — so this fills
them, and leaves blank exactly the columns that require a human in the room.

    python -m evaluator.testing.session_summary --out data/evaluation/observations.csv

Then add the participant codes by hand and fill the blank columns from your
notes. The name-to-code mapping is not stored here and should not be stored in
this repository at all.
"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

SESSIONS = Path("data/sessions")

# Filled from the transcript.
DERIVED = [
    "session_id", "started_at", "questions_attempted", "passes", "failures",
    "generated_served", "minutes_on_first_question", "hint_shown",
    "model", "provider",
]

# Filled by the observer. These are the study; the columns above are context.
OBSERVED = [
    "participant_code",
    "recommendation_judged_reasonable",   # Y / N
    "reason_for_that_judgement",
    "hint_verdict",                       # helped / gave it away / useless
    "generated_question_solvable",        # Y / N / not served
    "verbatim_confusions",
    "breakages",
]


def minutes_on_first(history, started_at):
    """Wall-clock minutes from session start to the first attempt's end.

    Attempts carry a timestamp only from the logging change onward, so older
    transcripts return blank rather than a fabricated zero.
    """
    if not history or not started_at:
        return ""
    stamp = history[0].get("timestamp")
    if not stamp:
        return ""
    try:
        delta = datetime.fromisoformat(stamp) - datetime.fromisoformat(started_at)
    except ValueError:
        return ""
    return f"{delta.total_seconds() / 60:.1f}"


def summarise(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    history = data.get("history", [])
    served = data.get("served", [])

    return {
        "session_id": data.get("session_id", path.stem),
        "started_at": data.get("started_at", ""),
        "questions_attempted": len({a.get("question_id") for a in history}),
        "passes": sum(a.get("result") == "passed" for a in history),
        "failures": sum(a.get("result") != "passed" for a in history),
        # Generated questions carry the gen_ prefix; q_ is the curated bank.
        "generated_served": sum(str(q).startswith("gen_") for q in served),
        "minutes_on_first_question": minutes_on_first(history, data.get("started_at")),
        "hint_shown": sum(bool(a.get("hint_text")) for a in history),
        "model": data.get("model", ""),
        "provider": data.get("provider", ""),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=Path("data/evaluation/observations.csv"))
    args = parser.parse_args()

    files = sorted(SESSIONS.glob("*.json"))
    if not files:
        raise SystemExit(f"no transcripts in {SESSIONS}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=OBSERVED + DERIVED)
        writer.writeheader()
        for path in files:
            row = {k: "" for k in OBSERVED}
            row.update(summarise(path))
            writer.writerow(row)

    print(f"{len(files)} sessions -> {args.out}")
    print(f"filled: {', '.join(DERIVED)}")
    print(f"for you: {', '.join(OBSERVED)}")


if __name__ == "__main__":
    main()
