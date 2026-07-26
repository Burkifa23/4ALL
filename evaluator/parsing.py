import json
import re


def strip_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` fences if the model added them anyway."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def normalize_big_o(value: str) -> str:
    """Try to coerce whatever the model gave into a canonical form like 'O(N log N)'."""
    if not value:
        return "unknown"
    match = re.search(r"O\([^)]*\)", value)
    return match.group(0) if match else value.strip()


def clamp_score(value, default: int = 3) -> int:
    """Force a score into an int between 1 and 5, or fall back to a default."""
    try:
        num = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(5, num))


def parse_evaluation(raw_text: str, provider: str) -> dict:
    """
    Turn raw model text into a clean evaluation dict.
    Never raises — always returns something usable.
    """
    cleaned = strip_fences(raw_text)

    try:
        data = json.loads(cleaned)
        return {
            "provider": provider,
            "big_o_time": normalize_big_o(data.get("big_o_time", "")),
            "efficiency_score": clamp_score(data.get("efficiency_score")),
            "style_score": clamp_score(data.get("style_score")),
            "raw_feedback": data.get("feedback", ""),
        }
    except (json.JSONDecodeError, AttributeError):
        pass

    # Fallback: try to salvage a Big-O pattern and any numbers 1-5 via regex
    big_o_match = re.search(r"O\([^)]*\)", raw_text)
    numbers = re.findall(r"\b[1-5]\b", raw_text)

    return {
        "provider": provider,
        "big_o_time": big_o_match.group(0) if big_o_match else "unknown",
        "efficiency_score": clamp_score(numbers[0]) if len(numbers) > 0 else 3,
        "style_score": clamp_score(numbers[1]) if len(numbers) > 1 else 3,
        "raw_feedback": raw_text,
    }
