from contracts.types import LLMHint
from evaluator.client import make_client, complete
from evaluator.prompts import HINT_PROMPT_V2_SYSTEM, HINT_PROMPT_V1_USER_TEMPLATE

MAX_DESCRIPTION_CHARS = 1000


def truncate_description(description: str) -> str:
    if len(description) > MAX_DESCRIPTION_CHARS:
        return description[:MAX_DESCRIPTION_CHARS] + "... [truncated]"
    return description


def get_hint(code: str, question: dict, failed_case_summary: str, byom_config: dict):
    client = make_client(byom_config)

    user_prompt = HINT_PROMPT_V1_USER_TEMPLATE.format(
        question_description=truncate_description(question.get("description_md", "")),
        code=code,
        failed_case_summary=failed_case_summary,
    )

    hint_text = complete(
        client=client,
        model=byom_config.get("model", "gemma2"),
        system=HINT_PROMPT_V2_SYSTEM,
        user=user_prompt,
        temperature=0.2,
        timeout=150.0,
    )

    # The contract type, not a dict — ui/results.py reads .hint_text, and
    # LLMHint is what contracts/types.py froze on Jul 31.
    return LLMHint(provider=byom_config.get("provider"), hint_text=hint_text)
