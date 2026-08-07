from openai import OpenAI


def make_client(byom_config: dict) -> OpenAI:
    """
    Build an OpenAI SDK client pointed at the right backend,
    based on the provider chosen in byom_config.

    base_url is optional and comes from the sidebar. It is what makes "bring
    your own model" real: "ollama" is really "any OpenAI-compatible server", so
    LM Studio, vLLM, llama.cpp or an Ollama on another host all work, with
    whatever model the user has pulled (qwen, deepseek-coder, codellama...).
    """
    provider = byom_config.get("provider")

    base_url = byom_config.get("base_url") or None

    if provider == "ollama":
        return OpenAI(
            base_url=base_url or "http://localhost:11434/v1",
            # Local servers ignore the key but the SDK requires a non-empty one.
            api_key=byom_config.get("api_key") or "ollama",
        )

    if provider == "openai":
        return OpenAI(
            api_key=byom_config.get("api_key"),
            base_url=base_url,
        )

    raise ValueError(f"Unknown provider: {provider}")


from evaluator.errors import map_error


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
        return response.choices[0].message.content
    except Exception as exc:
        raise map_error(exc)
