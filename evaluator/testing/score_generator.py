"""Score the served generator model — the .gguf, through a real server.

The notebook's scorecard measures the adapters in transformers. What ships is a
q4_k_m quantisation of a merge of those adapters, served over HTTP with the
Modelfile's sampling settings. Those are not the same artifact, and only this
one is what a student meets, so it gets its own number.

Nothing here re-implements the checks. It calls the same complete() the app
calls, the same _parse() that decides whether a reply is usable, the same
_fill_expected() that computes the test values, and the same _verify() that
runs the model's solution against them in the sandbox. Single-shot on purpose:
generate_question() retries twice with the failure fed back, which is the right
behaviour at serving time and the wrong one for a measurement.

So this measures the pipeline, not the raw model. The raw numbers — what the
model produced before expected values were computed for it — are kept in
scorecard_served.json for comparison.

    llama-server -m codegen-tutor_gguf/*.gguf --jinja -c 4096 -n 3072
    python -m evaluator.testing.score_generator --n 20
"""

import argparse
import json
import random
import time
from pathlib import Path

from evaluator.client import complete, make_client
from evaluator.errors import EvaluatorError
from evaluator.generate import (
    SYSTEM_PROMPT,
    _fill_expected,
    _parse,
    _verify,
    instruction,
)

QUESTIONS = Path("data/questions")


def requests(n, seed=42):
    """(topic, difficulty) pairs from the app's own question pool."""
    pool = sorted(
        {
            (record["topic"], record["difficulty"])
            for path in QUESTIONS.glob("*.json")
            for record in [json.loads(path.read_text(encoding="utf-8"))]
        }
    )
    if not pool:
        raise SystemExit(f"no questions in {QUESTIONS} to take topics from")

    rng = random.Random(seed)
    rng.shuffle(pool)

    if n <= len(pool):
        return pool[:n]

    # The pool only holds ~26 distinct pairs, so a bigger n has to reuse them.
    # That is sound here: the metric is what fraction of *requests* yield a
    # servable question, and generation is sampled at temperature 0.6, so the
    # same topic asked twice is an independent trial rather than a duplicate.
    # The unique pool still comes first and in the same order, so a larger run
    # remains comparable with the smaller ones that preceded it.
    return pool + [rng.choice(pool) for _ in range(n - len(pool))]


def score(client, model, pairs, timeout):
    counts = {"valid JSON": 0, "all 6 fields": 0, "tests self-consistent": 0}

    for topic, difficulty in pairs:
        started = time.time()
        try:
            raw = complete(
                client=client,
                model=model,
                system=SYSTEM_PROMPT,
                user=instruction(topic, difficulty),
                temperature=0.6,  # what models/Modelfile.codegen-tutor serves at
                timeout=timeout,
            )
        except EvaluatorError as exc:
            # .user_message is the app's UI copy and says to check the sidebar;
            # there is no sidebar here, so print what actually went wrong.
            print(f"  {topic:24} {exc.detail or exc.user_message}")
            continue

        print(f"  [{time.time() - started:.0f}s]", end="")

        # _parse() raises on both failures, so the two counters are separated by
        # which message comes back — "not JSON" is the ceiling/garbage case.
        try:
            record = _parse(raw, topic, difficulty)
        except EvaluatorError as exc:
            detail = (exc.detail or "")[:60]
            if not detail.startswith("not JSON"):
                counts["valid JSON"] += 1
            print(f"  {topic:24} rejected: {detail}")
            # The tail separates the two reasons a reply isn't JSON, which want
            # opposite fixes: cut off mid-value means the token ceiling is too
            # low, repeated fragments mean the model never learned to stop.
            print(f"      ...{raw[-200:]!r}")
            continue

        counts["valid JSON"] += 1
        counts["all 6 fields"] += 1

        # Same order as generate_question(): compute the expected values, then
        # verify. Skipping this would measure the model's arithmetic, which is
        # already known to be 0/20 and is no longer what decides what a student
        # gets — the pipeline does.
        problem = _fill_expected(record) or _verify(record)
        if problem is None:
            counts["tests self-consistent"] += 1
            print(f"  {topic:24} ok: {record['title']}")
        else:
            print(f"  {topic:24} unsound: {problem[:60]}")

    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8080/v1",
                        help="llama-server's default; Ollama is :11434/v1")
    parser.add_argument("--model", default="codegen-tutor",
                        help="ignored by llama-server, required by Ollama")
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=900.0,
                        help="per request; a 3B on CPU can take 6+ minutes")
    parser.add_argument("--out", type=Path, help="write the counts as JSON")
    args = parser.parse_args()

    pairs = requests(args.n)
    client = make_client({"base_url": args.base_url})

    print(f"{len(pairs)} requests to {args.base_url}\n")
    counts = score(client, args.model, pairs, args.timeout)

    print(f"\nserved model ({args.model})")
    for name, hits in counts.items():
        print(f"   {name:24} {hits}/{len(pairs)}  ({hits / len(pairs):.0%})")

    if args.out:
        args.out.write_text(json.dumps({"served": counts, "n": len(pairs)}, indent=2))
        print(f"\nsaved to {args.out}")


if __name__ == "__main__":
    main()
