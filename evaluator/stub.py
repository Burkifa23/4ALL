from contracts.types import LLMHint, LLMEvaluation


def get_hint(code, question, failed_case_summary, provider):

    return LLMHint(
        provider=provider, hint_text="Try checking your logic with smaller examples."
    )


def evaluate_complexity(code, question, provider):

    return LLMEvaluation(
        provider=provider,
        big_o_time="O(n)",
        efficiency_score=4,
        style_score=5,
        raw_feedback="Good solution structure.",
    )
