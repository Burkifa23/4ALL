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
