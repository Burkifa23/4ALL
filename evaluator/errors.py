from openai import (
    APIConnectionError,
    AuthenticationError,
    RateLimitError,
    APITimeoutError,
)


class EvaluatorError(Exception):
    """
    A friendly, user-facing error. Person 4's UI shows
    user_message directly to the student — never a raw
    stack trace from the SDK.
    """

    def __init__(self, user_message: str):
        self.user_message = user_message
        super().__init__(user_message)


def map_error(exc: Exception) -> EvaluatorError:
    """
    Turn a raw SDK exception into a friendly EvaluatorError.
    """
    if isinstance(exc, APIConnectionError):
        return EvaluatorError(
            "Couldn't reach the model. If you're using the local "
            "model, make sure Ollama is running (start it with "
            "'ollama serve')."
        )

    if isinstance(exc, AuthenticationError):
        return EvaluatorError(
            "Your API key was rejected. Please check the key in the sidebar."
        )

    if isinstance(exc, RateLimitError):
        return EvaluatorError(
            "Too many requests right now. Please wait a moment and try again."
        )

    if isinstance(exc, APITimeoutError):
        return EvaluatorError("The model took too long to respond. Please try again.")

    return EvaluatorError(
        "Something went wrong while contacting the model. Please try again."
    )
