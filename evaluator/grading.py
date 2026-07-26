import json
from evaluator.client import make_client, complete
from evaluator.prompts import GRADER_PROMPT_V1_SYSTEM, GRADER_PROMPT_V1_USER_TEMPLATE
from evaluator.testing.golden_set.golden_set import GOLDEN_SET


def evaluate_complexity(code: str, question: dict, byom_config: dict):
    client = make_client(byom_config)

    # pick two golden-set examples as Few-Shot demonstrations
    example_1 = GOLDEN_SET[0]
    example_2 = GOLDEN_SET[1]

    example_1_answer = json.dumps(
        {
            "big_o_time": example_1["true_big_o"],
            "efficiency_score": example_1["efficiency_score"],
            "style_score": example_1["style_score"],
            "feedback": example_1["justification"],
        }
    )
    example_2_answer = json.dumps(
        {
            "big_o_time": example_2["true_big_o"],
            "efficiency_score": example_2["efficiency_score"],
            "style_score": example_2["style_score"],
            "feedback": example_2["justification"],
        }
    )

    user_prompt = GRADER_PROMPT_V1_USER_TEMPLATE.format(
        example_1_code=example_1["code"],
        example_1_answer=example_1_answer,
        example_2_code=example_2["code"],
        example_2_answer=example_2_answer,
        code=code,
    )

    raw_text = complete(
        client=client,
        model=byom_config.get("model", "gemma2"),
        system=GRADER_PROMPT_V1_SYSTEM,
        user=user_prompt,
        temperature=0.2,
        timeout=90.0,
    )

    return raw_text  # parsing.py will clean this up tomorrow (Day 5)
