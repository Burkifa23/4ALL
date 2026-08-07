from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    APITimeoutError,
)


class EvaluatorError(Exception):
    """
    A friendly, user-facing error. Person 4's UI shows
    user_message directly to the student — never a raw
    stack trace from the SDK.

    detail carries the technical cause (exception type, HTTP status, whatever
    the server actually said). The UI hides it behind an expander: a student
    doesn't need it, but whoever is setting the model up does, and without it
    every misconfiguration looks identical.
    """

    def __init__(self, user_message: str, detail: str | None = None):
        self.user_message = user_message
        self.detail = detail
        super().__init__(user_message)


def map_error(exc: Exception) -> EvaluatorError:
    """
    Turn a raw SDK exception into a friendly EvaluatorError.

    Every branch attaches `detail` — the exception type, the HTTP status and
    whatever the server said. Without it every misconfiguration produces the
    same sentence and there is nothing to act on.
    """
    detail = _detail(exc)

    if isinstance(exc, APIConnectionError):
        return EvaluatorError(
            "Couldn't reach the model. If you're using a local model, make "
            "sure the server is running (Ollama: 'ollama serve'; LM Studio: "
            "start the server on the Developer tab) and that the Server URL "
            "in the sidebar matches its address.",
            detail,
        )

    if isinstance(exc, AuthenticationError):
        return EvaluatorError(
            "Your API key was rejected. Please check the key in the sidebar.",
            detail,
        )

    if isinstance(exc, RateLimitError):
        return EvaluatorError(
            "Too many requests right now. Please wait a moment and try again.",
            detail,
        )

    if isinstance(exc, APITimeoutError):
        return EvaluatorError(
            "The model took too long to respond. Local models can be slow — "
            "try a smaller model, or a shorter solution.",
            detail,
        )

    # A model name the server doesn't have, or one it can't load. Since the
    # sidebar accepts any model name, this is the most likely BYOM failure —
    # and the server's own message ("No models loaded", "Failed to load model
    # X") is far more actionable than anything we could write, so pass it
    # through rather than flattening it to "something went wrong".
    if isinstance(exc, (NotFoundError, APIStatusError)) and _is_model_problem(exc):
        return EvaluatorError(
            f"The model couldn't be used: {_server_message(exc)} "
            "Check the model name and Server URL in the sidebar.",
            detail,
        )

    return EvaluatorError(
        "Something went wrong while contacting the model. Open the details "
        "below to see what the server said, and check the Server URL and "
        "model name in the sidebar.",
        detail,
    )


def _detail(exc: Exception) -> str:
    """Technical cause, for the UI's collapsed details panel."""
    parts = [f"{type(exc).__name__}: {exc}"]

    status = getattr(exc, "status_code", None)
    if status is not None:
        parts.append(f"HTTP status: {status}")

    request = getattr(exc, "request", None)
    if request is not None and getattr(request, "url", None):
        parts.append(f"Request URL: {request.url}")

    return "\n".join(parts)


def _server_message(exc) -> str:
    """The message the server actually sent, or the raw string as a fallback."""
    try:
        body = exc.response.json()["error"]
        return body["message"] if isinstance(body, dict) else str(body)
    except Exception:
        return str(exc)


def _is_model_problem(exc) -> bool:
    status = getattr(exc, "status_code", None)
    return status in (400, 404) and "model" in _server_message(exc).lower()
