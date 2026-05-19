"""
Unified LLM client — dispatches to Ollama or Groq based on LLM_PROVIDER config.

Usage:
    from utils.llm_client import chat
    response = chat(messages=[...], json_mode=True, temperature=0)
"""
import json
import sys
sys.path.insert(0, ".")
import config
from loguru import logger


def chat(messages: list[dict], json_mode: bool = False, temperature: float = 0) -> str:
    """Send a chat request to the configured LLM and return the response text."""
    provider = config.LLM_PROVIDER.lower()

    if provider == "groq":
        return _groq_chat(messages, json_mode, temperature)
    else:
        return _ollama_chat(messages, json_mode, temperature)


def _ollama_chat(messages: list[dict], json_mode: bool, temperature: float) -> str:
    import ollama
    kwargs = {
        "model": config.OLLAMA_MODEL,
        "messages": messages,
        "options": {"temperature": temperature},
    }
    if json_mode:
        kwargs["format"] = "json"

    response = ollama.chat(**kwargs)
    return response["message"]["content"]


def _groq_chat(messages: list[dict], json_mode: bool, temperature: float) -> str:
    from groq import Groq
    client = Groq(api_key=config.GROQ_API_KEY)
    kwargs = {
        "model": config.GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content
