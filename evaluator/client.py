from openai import OpenAI


def make_client(byom_config: dict) -> OpenAI:
    """
    Build an OpenAI SDK client pointed at the right backend,
    based on the provider chosen in byom_config.
    """
    provider = byom_config.get("provider")

    if provider == "ollama":
        return OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        )

    if provider == "openai":
        return OpenAI(
            api_key=byom_config.get("api_key"),
        )

    raise ValueError(f"Unknown provider: {provider}")


from evaluator.errors import map_error


def complete(
    client: OpenAI,
    model: str,
    system: str,
    user: str,
    temperature: float = 0.2,
    timeout: float = 30.0,
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
        return response.choices[0].message.content
    except Exception as exc:
        raise map_error(exc)
