"""
Unified LLM client — dispatches to Ollama or Groq based on config or runtime override.

Usage:
    from utils.llm_client import chat, set_provider
    set_provider("ollama", model="mistral")   # optional runtime override
    response = chat(messages=[...], json_mode=True, temperature=0)
"""
import sys
sys.path.insert(0, ".")
import config
from loguru import logger

# Runtime overrides — set by UI before running pipeline
_provider_override: str | None = None
_model_override: str | None = None


def set_provider(provider: str, model: str | None = None) -> None:
    global _provider_override, _model_override
    _provider_override = provider.lower()
    _model_override = model


def get_active_provider() -> tuple[str, str]:
    provider = (_provider_override or config.LLM_PROVIDER).lower()
    if provider == "groq":
        model = _model_override or config.GROQ_MODEL
    else:
        model = _model_override or config.OLLAMA_MODEL
    return provider, model


def chat(messages: list[dict], json_mode: bool = False, temperature: float = 0) -> str:
    provider, model = get_active_provider()
    logger.debug(f"LLM call → provider={provider} model={model}")

    if provider == "groq":
        return _groq_chat(messages, model, json_mode, temperature)
    return _ollama_chat(messages, model, json_mode, temperature)


def _ollama_chat(messages: list[dict], model: str, json_mode: bool, temperature: float) -> str:
    import ollama
    kwargs: dict = {
        "model": model,
        "messages": messages,
        "options": {"temperature": temperature},
    }
    if json_mode:
        kwargs["format"] = "json"
    response = ollama.chat(**kwargs)
    return response["message"]["content"]


def _groq_chat(messages: list[dict], model: str, json_mode: bool, temperature: float) -> str:
    from groq import Groq
    client = Groq(api_key=config.GROQ_API_KEY)
    kwargs: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content
