from dataclasses import dataclass
from typing import Optional, Literal


@dataclass
class SandboxResult:
    status: Literal["passed", "failed", "blocked", "error", "timeout"]

    tests_passed: int
    tests_total: int

    failed_case_summary: Optional[str]

    security_alert: Optional[str]

    stdout: str

    runtime_ms: int


@dataclass
class LLMHint:
    provider: Literal["ollama", "openai"]

    hint_text: str


@dataclass
class LLMEvaluation:
    provider: Literal["ollama", "openai"]

    big_o_time: str

    efficiency_score: int

    style_score: int

    raw_feedback: str


@dataclass
class FeatureVector:
    """Person 4 assembles this -> Person 3's recommender consumes it.

    Built by recommender.features.assemble_features(), which is the single
    source of truth for every definition and cold-start default below.
    """

    question_id: str

    question_difficulty: int  # 1=Easy 2=Medium 3=Hard

    question_topic: str

    attempts_on_question: int

    user_pass_rate: float  # 0.0-1.0 over the whole session

    avg_efficiency_score: float

    avg_style_score: float

    last_efficiency_score: int

    last_style_score: int


@dataclass
class Recommendation:
    """Person 3's recommender produces this -> Person 4 serves the question."""

    next_question_id: str

    decision: Literal["reinforce", "level_up"]

    confidence: float
