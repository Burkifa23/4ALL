"""Checks for the generated-question path. Plain asserts, no framework:
`python tests/test_generated_question.py`.

The one that matters is test_verify_rejects_broken_test_case. Everything else
about a model-written question can be eyeballed on the page; whether its test
cases are actually the ones its solution passes cannot, and serving a question
that fails that check hands the student something unsolvable.

No network: the model's output is a fixture string, so this runs anywhere.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.ingest.validates_questions import REQUIRED_FIELDS  # noqa: E402
from evaluator.errors import EvaluatorError  # noqa: E402
from evaluator.generate import SYSTEM_PROMPT, _parse, _verify  # noqa: E402
from sandbox import runner  # noqa: E402
from sandbox.runner import register_question, run_submission  # noqa: E402

MODELFILE = Path(__file__).resolve().parent.parent / "models" / "Modelfile.codegen-tutor"

# What a well-behaved CodeGenTutor returns: the six taught fields, nothing else.
MODEL_OUTPUT = json.dumps(
    {
        "title": "Maximum Sum Of A Window",
        "description_md": (
            "Given an integer array `nums` and an integer `k`, return the "
            "largest sum of any contiguous subarray of length `k`.\n\n"
            "Example:\n\nInput: nums = [1,4,2,10], k = 2\nOutput: 12\n\n"
            "Constraints:\n\n1 <= k <= len(nums) <= 1000"
        ),
        "starter_code": (
            "class Solution:\n"
            "    def maxWindowSum(self, nums: List[int], k: int) -> int:\n"
            "        pass\n"
        ),
        "entry_point": "Solution().maxWindowSum",
        "reference_solution": (
            "class Solution:\n"
            "    def maxWindowSum(self, nums: List[int], k: int) -> int:\n"
            "        window = sum(nums[:k])\n"
            "        best = window\n"
            "        for i in range(k, len(nums)):\n"
            "            window += nums[i] - nums[i - k]\n"
            "            best = max(best, window)\n"
            "        return best\n"
        ),
        "test_cases": [
            {"input": {"nums": [1, 4, 2, 10], "k": 2}, "expected": 12},
            {"input": {"nums": [1, 1, 1, 1], "k": 4}, "expected": 4},
            {"input": {"nums": [5], "k": 1}, "expected": 5},
            {"input": {"nums": [-1, -2, -3], "k": 2}, "expected": -3},
            {"input": {"nums": [2, 3, 4, 1, 5], "k": 3}, "expected": 10},
            {"input": {"nums": [0, 0, 9], "k": 1}, "expected": 9},
        ],
    }
)


def record():
    return _parse(MODEL_OUTPUT, "Sliding Window", 2)


def test_parse_fills_the_whole_schema():
    data = record()

    # The model is taught six fields; the rest is bookkeeping this module owes
    # the sandbox, the recommender and the validator.
    assert not REQUIRED_FIELDS - data.keys(), REQUIRED_FIELDS - data.keys()

    assert data["difficulty"] == 2, "difficulty comes from the request, not the model"
    assert data["topic"] == "Sliding Window"
    assert data["test_case_count"] == 6

    # from typing import * — the model writes List[int] hints and never has to
    # remember the import.
    assert "from typing import *" in data["reference_solution"]

    # Never q_*: that prefix is what sandbox.runner and recommender.engine glob
    # for on disk, so a generated question must not be able to land in either.
    assert data["question_id"].startswith("gen_")


def test_verify_accepts_a_consistent_question():
    assert _verify(record()) is None


def test_verify_rejects_broken_test_case():
    """The hallucination gate: solution and tests must actually agree."""
    broken = record()
    broken["question_id"] = "gen_broken"
    broken["test_cases"] = [dict(c) for c in broken["test_cases"]]
    broken["test_cases"][0]["expected"] = 999  # model got one answer wrong

    problem = _verify(broken)

    assert problem is not None, "a wrong expected value must not reach a student"
    assert "5/6" in problem, problem


def test_verify_rejects_a_solution_that_does_not_run():
    crashing = record()
    crashing["question_id"] = "gen_crash"
    crashing["reference_solution"] = "class Solution:\n    def maxWindowSum(self):\n        return undefined_name\n"

    assert _verify(crashing) is not None


def test_registering_does_not_hide_the_questions_on_disk():
    """Regression: the cache is primed lazily and an empty cache means
    "not loaded yet", so registering into a cold one used to make every real
    question vanish."""
    runner._question_cache.clear()

    register_question(record())

    on_disk = sorted(runner.QUESTIONS_DIR.glob("q_*.json"))

    if not on_disk:
        print("    (skipped disk half: data/questions is empty — run the ingest)")
        return

    real_id = json.loads(on_disk[0].read_text(encoding="utf-8"))["question_id"]

    assert real_id in runner._question_cache


def test_bad_model_output_raises_a_student_facing_error():
    for bad in ("I'd be happy to help!", "{}", json.dumps({"title": "x"})):
        try:
            _parse(bad, "Array", 1)
        except EvaluatorError as exc:
            assert exc.user_message and exc.detail
        else:
            raise AssertionError(f"{bad!r} should have been rejected")


def test_modelfile_system_prompt_matches_training():
    """A model served with a different system prompt than it was tuned on is a
    working fine-tune that looks broken. Two copies exist because a Modelfile
    can't import Python — so check them instead of trusting a comment."""
    match = re.search(r'SYSTEM """(.*?)"""', MODELFILE.read_text(encoding="utf-8"), re.S)

    assert match, "no SYSTEM block in the Modelfile"
    assert match.group(1).strip() == SYSTEM_PROMPT.strip()


if __name__ == "__main__":
    import tempfile

    from evaluator import generate

    # Don't drop fixture questions into the repo's provenance folder.
    generate.GENERATED_DIR = Path(tempfile.mkdtemp()) / "generated"

    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("\nall checks passed")
