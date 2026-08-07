"""Offline stand-in for the real evaluator.

Signatures and return types match evaluator.hints / evaluator.grading exactly,
so app.py can swap between them with EVALUATOR_MODE=stub and nothing else
changes. Used by the test suite (no Ollama, no 90-second waits) and as the
demo fallback if the local model dies.
"""

from contracts.types import LLMHint, LLMEvaluation


def get_hint(code, question, failed_case_summary, byom_config):

    return LLMHint(
        provider=byom_config.get("provider"),
        hint_text="Try checking your logic with smaller examples.",
    )


def evaluate_complexity(code, question, byom_config):

    return LLMEvaluation(
        provider=byom_config.get("provider"),
        big_o_time="O(n)",
        efficiency_score=4,
        style_score=5,
        raw_feedback="Good solution structure.",
    )
