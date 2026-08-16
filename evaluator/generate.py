"""Generate a practice question on demand, in the same schema as data/questions/.

Two consumers, one source of truth:

  * notebooks/finetune_codegen_tutor.ipynb imports SYSTEM_PROMPT, instruction()
    and TAUGHT_FIELDS to build the SFT training targets.
  * app.py imports generate_question() to serve a custom topic at runtime.

Anything that drifts between those two breaks the fine-tune silently — the model
would be trained against one prompt and served another — so they share these
constants rather than each keeping a copy.

The model is only ever taught SIX fields. `difficulty` and `topic` are inputs
to the instruction, so teaching it to echo them back is wasted tokens and one
more thing to disagree with; the remaining schema fields
(question_id, topics, test_case_count, optimal_complexity, source_*) are
bookkeeping this module fills in.
"""

import json
import re
from pathlib import Path
from typing import Optional

from evaluator.client import complete, make_client
from evaluator.errors import EvaluatorError
from evaluator.parsing import strip_fences

GENERATED_DIR = Path("data/generated")

DIFFICULTY_NAMES = {1: "Easy", 2: "Medium", 3: "Hard"}

# The model writes these; everything else in the schema is filled by _finalize().
TAUGHT_FIELDS = (
    "title",
    "description_md",
    "starter_code",
    "entry_point",
    "reference_solution",
    "test_cases",
)

# Prepended to whatever solution the model writes, so it never has to spend
# tokens on imports and can't forget one.
#
# Deliberately the same list, in the same order, as the preamble the ingest
# pipeline leaves on every data/questions/*.json reference solution — the
# fine-tune is trained on solutions that ran under exactly these names, and
# `from math import *` last (shadowing builtins.pow) is part of that. Dropped:
# the tree/linked-list helpers, since ingest_leetcode.uses_tree_or_list_structure
# filters those problems out of the training set entirely.
SOLUTION_PREAMBLE = """import random
import functools
import collections
import string
import math
import datetime

from typing import *
from functools import *
from collections import *
from itertools import *
from heapq import *
from bisect import *
from string import *
from operator import *
from math import *

inf = float('inf')

"""

SYSTEM_PROMPT = """You are a programming-exercise generator. You reply with a \
single JSON object and nothing else — no prose, no markdown fences.

The object has exactly these keys:

  "title"              A short human-readable name for the problem.
  "description_md"     The problem statement, with a worked Example and a
                       Constraints section, as markdown.
  "starter_code"       A `class Solution:` block with one method, correct type
                       hints, and a body of `pass`.
  "entry_point"        "Solution().<methodName>", matching starter_code exactly.
  "reference_solution" The same class and method, correctly implemented.
  "test_cases"         A list of 6 to 10 objects, each {"input": {...}}.
                       "input" maps the method's parameter names to values.
                       Include the edge cases, and do not write expected
                       values: they are computed by running your solution.

Every input must be one the reference solution runs on without error. Only the \
standard library may be used."""


def instruction(topic: str, difficulty: int) -> str:
    """The user turn. Identical at training time and at serving time."""
    name = DIFFICULTY_NAMES.get(difficulty, "Medium")
    return f"Generate a {name} Python programming challenge about {topic}."


def _next_id() -> str:
    """gen_0001, gen_0002, ... Never q_*, which is what the recommender's
    question pool and the sandbox's disk loader glob for — a generated question
    must not be able to leak into either."""
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    used = [int(m.group(1)) for p in GENERATED_DIR.glob("gen_*.json")
            if (m := re.fullmatch(r"gen_(\d+)", p.stem))]
    return f"gen_{max(used, default=0) + 1:04d}"


def _finalize(taught: dict, topic: str, difficulty: int) -> dict:
    """Model output + the bookkeeping fields -> a full question record.

    Field names and the required set come from data/ingest/validates_questions.py.
    """
    return {
        "question_id": _next_id(),
        "title": taught["title"],
        "difficulty": difficulty,
        "topic": topic,
        "topics": [topic],
        "description_md": taught["description_md"],
        "starter_code": taught["starter_code"],
        "entry_point": taught["entry_point"],
        "reference_solution": SOLUTION_PREAMBLE + taught["reference_solution"],
        "test_cases": taught["test_cases"],
        "test_case_count": len(taught["test_cases"]),
        "optimal_complexity": None,
        "source_task_id": None,
        "source_question_id": None,
        "generated": True,
    }


def _parse(raw_text: str, topic: str, difficulty: int) -> dict:
    """Raw completion -> question record, or raise EvaluatorError."""
    try:
        taught = json.loads(strip_fences(raw_text))
    except (json.JSONDecodeError, TypeError) as exc:
        raise EvaluatorError(
            "The generator model did not return a usable question.",
            detail=f"not JSON ({exc}): {raw_text[:500]}",
        )

    missing = [f for f in TAUGHT_FIELDS if not taught.get(f)]
    if missing:
        raise EvaluatorError(
            "The generator model returned an incomplete question.",
            detail=f"missing or empty fields: {missing}",
        )

    if not isinstance(taught["test_cases"], list):
        raise EvaluatorError(
            "The generator model returned an incomplete question.",
            detail=f"test_cases was {type(taught['test_cases']).__name__}, not a list",
        )

    return _finalize(taught, topic, difficulty)


# A 6-10 case schema that loses more than a few cases to exceptions is a
# solution that half works, not a question worth serving.
MIN_TEST_CASES = 4


def _fill_expected(record: dict) -> Optional[str]:
    """Replace the model's guessed `expected` values with what its reference
    solution really returns. Returns None when the question is usable, else why
    it isn't.

    The schema asks the model to write working Python and then state, from
    memory, what that code returns for each input — which is asking a 3B to be
    an interpreter. It measured 0/20 on held-out topics, and no amount of
    further fine-tuning addresses it (docs/codegen_tutor_findings.md).

    So this does not *check* the expected values, it *defines* them. Every case
    the solution actually runs becomes self-consistent by construction, and
    what remains is a question that may not match its own prose — a far better
    failure than one no student can finish.

    Imported here, not at module scope, for the same reason _verify() is:
    evaluator/ is otherwise sandbox-free so evaluator/stub.py can stand in.
    """
    from sandbox.runner import solution_outputs

    outputs = solution_outputs(record)

    if not outputs:
        return "the reference solution did not run at all"

    # Built explicitly rather than {**case, ...}: a model told not to write
    # expected values will invent its own key for them anyway ("output" is the
    # one seen in practice), and a test case carrying two answer fields that
    # disagree is a question record nobody can read with confidence.
    # A computed None is dropped, not kept. It nearly always means the solution
    # ran off the end through a branch it never wrote — the model borrows a
    # problem whose statement guarantees a match, writes the idiomatic solution
    # with no no-match return, then invents an input with no match. Recording
    # that None as the spec produces a question the description says is
    # impossible, annotated -> List[int], that no correct reading can pass.
    cases = [
        {"input": case["input"], "expected": output["value"]}
        for case, output in zip(record["test_cases"], outputs)
        if output["ok"] and output["value"] is not None
    ]

    if len(cases) < MIN_TEST_CASES:
        return (
            f"only {len(cases)} of {len(outputs)} test inputs produced a usable "
            f"result, need {MIN_TEST_CASES}"
        )

    values = [case["expected"] for case in cases]

    # Computing expected by execution makes the tests true by construction —
    # including for a solution that returns None for everything, which would
    # yield a question passable by `return None`. That is the one new way this
    # approach can hand out a worthless question, so it is the one it checks.
    if all(value == values[0] for value in values):
        return f"every test case expects {values[0]!r}, so a stub would pass"

    if not any(values):
        return "every test case expects a falsy value, so a stub would pass"

    record["test_cases"] = cases
    record["test_case_count"] = len(cases)
    return None


def _verify(record: dict) -> Optional[str]:
    """Run the model's own solution against the model's own tests.

    This is the hallucination gate. A model that invents a plausible-looking
    problem and then gets one `expected` value wrong hands the student an
    unsolvable question, and there is no way to spot that by reading the JSON —
    the tests have to actually run.

    Imported here rather than at module scope: evaluator/ is otherwise
    sandbox-free, and evaluator/stub.py exists so the app can run with no model
    at all. Returns None when the question is sound, else why it isn't.
    """
    from sandbox.runner import register_question, run_submission

    register_question(record)
    result = run_submission(record["reference_solution"], record["question_id"])

    if result.status == "passed":
        return None

    return (
        f"{result.status}: {result.tests_passed}/{result.tests_total} of its own "
        f"test cases passed - {result.failed_case_summary or result.security_alert}"
    )


def generate_question(topic: str, difficulty: int, byom_config: dict,
                      model: Optional[str] = None, attempts: int = 2) -> dict:
    """A question record for `topic` at `difficulty`, verified to be solvable.

    model: overrides byom_config["model"] — the fine-tuned generator
    (CodeGenTutor) is usually a different model from the grader, on the same
    endpoint. Everything else about the connection is the sidebar's BYOM config,
    so no new client code exists for this path.

    Raises EvaluatorError if every attempt produced unusable output; app.py
    already renders that with .user_message.
    """
    config = {**byom_config, "model": model or byom_config.get("model")}
    client = make_client(config)
    user = instruction(topic, difficulty)
    problems = []

    for attempt in range(attempts):
        raw = complete(
            client=client,
            model=config["model"],
            system=SYSTEM_PROMPT,
            # The expected values are computed now, so there is no point asking
            # the model to get them right — what it still has to get right is a
            # solution that runs on every input it invented.
            user=user if attempt == 0 else (
                f"{user}\n\nYour last attempt was rejected ({problems[-1]}). "
                "Return only the JSON object, and make sure the reference "
                "solution runs without error on every test input."
            ),
            # Higher than the grader's 0.2: two students asking for the same
            # topic should not get the same question back.
            temperature=0.6,
            timeout=180.0,
        )

        try:
            record = _parse(raw, topic, difficulty)
        except EvaluatorError as exc:
            problems.append(exc.detail or exc.user_message)
            continue

        # Before verifying, replace the model's guessed expected values with the
        # real ones. _verify() below stops being a coin flip and becomes an
        # assertion that this worked.
        problem = _fill_expected(record)
        if problem is not None:
            problems.append(problem)
            continue

        problem = _verify(record)
        if problem is None:
            _save(record)
            return record

        problems.append(problem)

    raise EvaluatorError(
        f"Could not generate a working {DIFFICULTY_NAMES.get(difficulty, '')} "
        f"question about {topic} after {attempts} tries. Try a different topic, "
        "or pick a question from the track.",
        detail="\n".join(f"attempt {i + 1}: {p}" for i, p in enumerate(problems)),
    )


def _save(record: dict) -> None:
    """Provenance for the report: what the model actually produced.

    NOT data/questions/ — that folder is the recommender's question pool and
    the Week 13 evaluation set. Never let a write failure lose a question the
    student is about to be served, same reasoning as ui/history.save_session.
    """
    try:
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        path = GENERATED_DIR / f"{record['question_id']}.json"
        path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    except OSError:
        pass
