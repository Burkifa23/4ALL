from evaluator.client import make_client, complete
from evaluator.prompts import HINT_PROMPT_V1_SYSTEM, HINT_PROMPT_V1_USER_TEMPLATE


def get_hint(code: str, question: dict, failed_case_summary: str, byom_config: dict):
    client = make_client(byom_config)

    user_prompt = HINT_PROMPT_V1_USER_TEMPLATE.format(
        question_description=question.get("description", ""),
        code=code,
        failed_case_summary=failed_case_summary,
    )

    hint_text = complete(
        client=client,
        model=byom_config.get("model", "gemma2"),
        system=HINT_PROMPT_V1_SYSTEM,
        user=user_prompt,
        temperature=0.2,
    )

    return {
        "provider": byom_config.get("provider"),
        "hint_text": hint_text,
    }
