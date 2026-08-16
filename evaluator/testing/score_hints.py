"""Score the hint path the way docs/gemma_scoring_notes.md scored the grader.

HINT_PROMPT_V1_SYSTEM has never been iterated and has no baseline, while the
grader prompt went V1 -> V2 -> V3 against a golden set. This is the missing half.

The rubric is the prompt's own four rules, so a violation is a fact rather than
a matter of taste: no corrected code, name the concept THIS student is missing,
reference the failing case, stay under 120 words. Whether the named concept is
the *right* one still needs a human — the hints are printed for blind rating,
per docs/human_rating_guide.md.

    llama-server -m models/codegen-tutor.Q4_K_M.gguf --jinja -c 8192 ...
    python -m evaluator.testing.score_hints --prompt v1
"""

import argparse
import difflib
import json
import re
from pathlib import Path

from evaluator.client import complete, make_client
from evaluator.errors import EvaluatorError
from evaluator.prompts import (
    HINT_PROMPT_V1_SYSTEM,
    HINT_PROMPT_V1_USER_TEMPLATE,
    HINT_PROMPT_V2_SYSTEM,
)
from sandbox.runner import register_question, run_submission

QUESTIONS = Path("data/questions")

# The example embedded in V1's own rules. A small model repeats it verbatim
# instead of reading the student's code, which is the defect this measures.
V1_EXAMPLE = "consider what happens when the list is empty"

PROMPTS = {"v1": HINT_PROMPT_V1_SYSTEM, "v2": HINT_PROMPT_V2_SYSTEM}

# Ten real questions, each with a submission carrying one classic bug and one
# nameable missing idea. The `concept` field is what a human rates the hint
# against; nothing automated reads it.
HINT_SET = [
    {"qid": "q_0007", "concept": "the stones must be smashed repeatedly, not once",
     "code": "class Solution:\n    def lastStoneWeight(self, stones):\n        return max(stones) - min(stones)\n"},
    {"qid": "q_0008", "concept": "proper divisors exclude the number itself",
     "code": "class Solution:\n    def checkPerfectNumber(self, num):\n        return sum(i for i in range(1, num + 1) if num % i == 0) == num\n"},
    {"qid": "q_0011", "concept": "the centre cell of an odd matrix is on both diagonals",
     "code": "class Solution:\n    def diagonalSum(self, mat):\n        n = len(mat)\n        return sum(mat[i][i] for i in range(n)) + sum(mat[i][n - 1 - i] for i in range(n))\n"},
    {"qid": "q_0012", "concept": "letter counts matter, not just which letters appear",
     "code": "class Solution:\n    def isAnagram(self, s, t):\n        return set(s) == set(t)\n"},
    {"qid": "q_0014", "concept": "the first and last beds have only one neighbour",
     "code": "class Solution:\n    def canPlaceFlowers(self, flowerbed, n):\n        count = 0\n        for i in range(1, len(flowerbed) - 1):\n            if flowerbed[i] == 0 and flowerbed[i - 1] == 0 and flowerbed[i + 1] == 0:\n                flowerbed[i] = 1\n                count += 1\n        return count >= n\n"},
    {"qid": "q_0005", "concept": "removing a pair can create a new adjacent pair",
     "code": "class Solution:\n    def minLength(self, s):\n        s = s.replace('AB', '').replace('CD', '')\n        return len(s)\n"},
    {"qid": "q_0003", "concept": "equal values must share a rank",
     "code": "class Solution:\n    def arrayRankTransform(self, arr):\n        order = sorted(arr)\n        return [order.index(x) + 1 for x in arr]\n"},
    {"qid": "q_0010", "concept": "n characters need n+1 distinct numbers",
     "code": "class Solution:\n    def diStringMatch(self, s):\n        return [i for i in range(len(s))]\n"},
    {"qid": "q_0001", "concept": "every round removes the largest from each row",
     "code": "class Solution:\n    def deleteGreatestValue(self, grid):\n        return sum(max(row) for row in grid)\n"},
    {"qid": "q_0004", "concept": "a '#' marks the two digits before it as one letter",
     "code": "class Solution:\n    def freqAlphabets(self, s):\n        return ''.join(chr(96 + int(c)) for c in s if c.isdigit())\n"},
]


def load(qid):
    return json.loads((QUESTIONS / f"{qid}.json").read_text(encoding="utf-8"))


def rate(hint, code, failed_case_summary):
    """The prompt's own rules, checked mechanically."""
    words = len(hint.split())
    lowered = hint.lower()

    # Identifiers the student actually wrote, so a hint about "the list" scores
    # differently from one naming their own variable.
    names = set(re.findall(r"\b[a-z_][a-z_0-9]{2,}\b", code.lower())) - {
        "self", "class", "def", "return", "for", "range", "len", "solution", "int", "str"
    }

    # Literals from the failing case: "got 5, expected 3" -> 5, 3
    literals = set(re.findall(r"-?\d+", failed_case_summary))

    return {
        "no_code": not any(m in hint for m in ("```", "def ", "return ", "class ")),
        "under_120w": words <= 120,
        "cites_case": bool(literals & set(re.findall(r"-?\d+", hint))),
        "grounded": any(n in lowered for n in names),
        "not_echo": difflib.SequenceMatcher(None, lowered.strip(" ."), V1_EXAMPLE).ratio() < 0.8,
        "words": words,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", choices=sorted(PROMPTS), default="v1")
    parser.add_argument("--base-url", default="http://localhost:8080/v1")
    parser.add_argument("--model", default="codegen-tutor")
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    client = make_client({"base_url": args.base_url})
    system = PROMPTS[args.prompt]
    rules = ["no_code", "under_120w", "cites_case", "grounded", "not_echo"]
    totals = dict.fromkeys(rules, 0)
    rows = []

    print(f"HINT_PROMPT {args.prompt.upper()} over {len(HINT_SET)} submissions\n")

    for case in HINT_SET:
        question = load(case["qid"])
        register_question(question)
        result = run_submission(case["code"], question["question_id"])

        if not result.failed_case_summary:
            print(f"  {case['qid']}  SKIPPED - submission did not fail ({result.status})")
            continue

        user = HINT_PROMPT_V1_USER_TEMPLATE.format(
            question_description=question["description_md"][:1000],
            code=case["code"],
            failed_case_summary=result.failed_case_summary,
        )

        try:
            hint = complete(client=client, model=args.model, system=system,
                            user=user, temperature=0.2, timeout=args.timeout)
        except EvaluatorError as exc:
            print(f"  {case['qid']}  ERROR {exc.detail or exc.user_message}")
            continue

        scores = rate(hint, case["code"], result.failed_case_summary)
        for rule in rules:
            totals[rule] += int(scores[rule])

        broke = [r for r in rules if not scores[r]]
        print(f"  {case['qid']}  [{scores['words']}w] {'PASS' if not broke else 'breaks ' + ','.join(broke)}")
        print(f"      should name: {case['concept']}")
        print(f"      said:        {hint.strip()[:300]}\n")
        rows.append({"qid": case["qid"], "concept": case["concept"],
                     "hint": hint.strip(), **scores})

    n = len(rows)
    print("=" * 60)
    print(f"{args.prompt.upper()}  ({n} rated)")
    for rule in rules:
        print(f"   {rule:14} {totals[rule]}/{n}")

    if args.out:
        args.out.write_text(json.dumps(
            {"prompt": args.prompt, "n": n,
             "totals": {r: totals[r] for r in rules}, "hints": rows}, indent=2))
        print(f"\nsaved to {args.out}")


if __name__ == "__main__":
    main()
