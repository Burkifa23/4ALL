from urllib.parse import urlparse

from openai import OpenAI

from evaluator.errors import EvaluatorError, map_error


def normalise_base_url(url: str) -> str:
    """Append /v1 when the user gives a bare host.

    LM Studio and Ollama both show their address as `http://localhost:1234`,
    so that is what people paste — but the OpenAI SDK appends `/chat/completions`
    directly to it, producing `/chat/completions` instead of
    `/v1/chat/completions`. LM Studio answers that with **HTTP 200** and an
    error body rather than a 404, so the failure used to surface as an
    unhelpful "Something went wrong".

    Only a bare host is touched; an explicit path is left alone, since some
    servers are mounted somewhere other than /v1.
    """
    if not url:
        return url

    parsed = urlparse(url.strip())

    if parsed.path in ("", "/"):
        return f"{url.strip().rstrip('/')}/v1"

    return url.strip()


# Fallback endpoints for configs that carry a provider name but no base_url —
# older callers and Person 2's test scripts do this. A lookup table, not
# branching logic: the provider name never decides behaviour, it only supplies
# a default that base_url overrides.
LEGACY_BASE_URLS = {
    "ollama": "http://localhost:11434/v1",
    "openai": "https://api.openai.com/v1",
}


def make_client(byom_config: dict) -> OpenAI:
    """Build an OpenAI SDK client for whatever endpoint byom_config names.

    **The provider name decides nothing.** Anything speaking the OpenAI API
    works — Ollama, LM Studio, vLLM, llama.cpp, OpenAI, Groq, OpenRouter,
    Together, DeepSeek, a company gateway — because the only things that matter
    are the URL, the key and the model, all of which come from the sidebar.

    This used to branch on the provider name, which hardcoded "cloud" to mean
    "OpenAI": a Groq key was sent to api.openai.com and rejected with a 401.
    """
    base_url = normalise_base_url(byom_config.get("base_url") or "")

    if not base_url:
        base_url = LEGACY_BASE_URLS.get(byom_config.get("provider"))

    if not base_url:
        # Without this the SDK quietly defaults to api.openai.com, which is the
        # same wrong assumption in a lower layer: a Groq key would go to OpenAI
        # and come back 401. Fail with something the user can act on instead.
        raise EvaluatorError(
            "No server URL is set for this provider. Enter the endpoint in the "
            "sidebar — for example https://api.groq.com/openai/v1.",
            detail=f"byom_config had no usable base_url: {byom_config!r}",
        )

    return OpenAI(
        base_url=base_url,
        # Local servers ignore the key, but the SDK insists on a non-empty one.
        api_key=byom_config.get("api_key") or "not-needed",
    )


def fetch_models(byom_config: dict):
    """(model ids, reason it failed) from the endpoint's GET /v1/models.

    Uses the OpenAI-standard listing, which Ollama, LM Studio, OpenAI, Groq and
    OpenRouter all implement — so discovery works the same everywhere instead of
    being special-cased per provider.

    Never raises: the UI falls back to a free-text field, so nothing is ever
    gated behind this list. But it does report *why* it came up empty — a
    silent [] leaves the user typing a model name blind, which is how you end
    up sending `grok` to Groq and getting a 404.
    """
    try:
        models = sorted(m.id for m in make_client(byom_config).models.list())
        return models, None if models else "the endpoint returned an empty list"
    except EvaluatorError as exc:
        return [], exc.user_message
    except Exception as exc:
        return [], _short_reason(exc)


def list_models(byom_config: dict) -> list:
    """Model ids the endpoint reports, or [] if it doesn't say."""
    return fetch_models(byom_config)[0]


def _short_reason(exc: Exception) -> str:
    """One line a user can act on, not a stack trace."""
    status = getattr(exc, "status_code", None)

    if status == 401:
        return "the API key was rejected (401)"

    if status == 404:
        return "this endpoint has no /models listing (404)"

    try:
        body = exc.response.json()["error"]
        message = body["message"] if isinstance(body, dict) else str(body)
        return f"{message} ({status})" if status else str(message)
    except Exception:
        return f"{type(exc).__name__}: {exc}"[:200]


def complete(
    client: OpenAI,
    model: str,
    system: str,
    user: str,
    temperature: float = 0.2,
    timeout: float = 120.0,
) -> str:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            timeout=timeout,
        )

        # A well-behaved server signals failure with a 4xx/5xx the SDK raises
        # on. Some local servers answer 200 with an error payload instead, and
        # then `choices` is None — indexing it would raise a TypeError that
        # map_error flattens into "something went wrong". Check explicitly so
        # the server's own explanation survives.
        if not response.choices:
            raise EvaluatorError(
                "The model server replied but sent no completion. If you are "
                "using a local server, check the Server URL — it usually needs "
                "to end with /v1.",
                detail=str(getattr(response, "error", None) or repr(response)[:500]),
            )

        return response.choices[0].message.content

    except EvaluatorError:
        raise
    except Exception as exc:
        raise map_error(exc)
