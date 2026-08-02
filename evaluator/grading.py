import json
from evaluator.client import make_client, complete
from evaluator.prompts import GRADER_PROMPT_V2_SYSTEM, GRADER_PROMPT_V1_USER_TEMPLATE
from evaluator.parsing import parse_evaluation, strip_fences
from evaluator.testing.golden_set.golden_set import GOLDEN_SET


def evaluate_complexity(code: str, question: dict, byom_config: dict):
    client = make_client(byom_config)
    provider = byom_config.get("provider")
    model = byom_config.get("model", "gemma2")

    example_1 = GOLDEN_SET[0]  # two_sum_brute — obvious O(N^2)
    example_2 = GOLDEN_SET[2]  # two_sum_optimal — O(N)
    example_3 = next(
        e for e in GOLDEN_SET if e["id"] == "reverse_string_brute"
    )  # hidden O(N^2)

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

    example_3_answer = json.dumps(
        {
            "big_o_time": example_3["true_big_o"],
            "efficiency_score": example_3["efficiency_score"],
            "style_score": example_3["style_score"],
            "feedback": example_3["justification"],
        }
    )

    user_prompt = f"""Here are three example evaluations:
Example 1:
Code:
{example_1["code"]}
Evaluation: {example_1_answer}

Example 2:
Code:
{example_2["code"]}
Evaluation: {example_2_answer}

Example 3 (note: single loop, but string concatenation inside makes it quadratic):
Code:
{example_3["code"]}
Evaluation: {example_3_answer}

Now evaluate this code:
{code}
"""

    raw_text = complete(
        client=client,
        model=model,
        system=GRADER_PROMPT_V2_SYSTEM,
        user=user_prompt,
        temperature=0.2,
        timeout=90.0,
    )

    try:
        json.loads(strip_fences(raw_text))
    except json.JSONDecodeError:
        raw_text = complete(
            client=client,
            model=model,
            system=GRADER_PROMPT_V2_SYSTEM,
            user=user_prompt
            + "\n\nYour last response was not valid JSON. Respond with ONLY the JSON object.",
            temperature=0.2,
            timeout=150.0,
        )

    return parse_evaluation(raw_text, provider)
