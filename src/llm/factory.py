"""Unified LLM factory: Groq (cloud free) or Ollama (local free)."""

from typing import Any, Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq

from src.config import settings

Provider = Literal["groq", "ollama", "auto"]


def llm_status(provider: Provider = "auto") -> dict[str, Any]:
    """Return which providers are available and the active choice."""
    ollama_ok = _ollama_reachable()
    groq_ok = settings.has_groq
    active = _resolve_provider(provider)
    return {
        "active": active,
        "groq_configured": groq_ok,
        "ollama_reachable": ollama_ok,
        "ollama_model": settings.ollama_model,
        "groq_model": settings.groq_model,
    }


def _ollama_reachable() -> bool:
    try:
        import httpx

        url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
        resp = httpx.get(url, timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False


def _resolve_provider(provider: Provider) -> str:
    if provider == "groq":
        if not settings.has_groq:
            raise ValueError("Groq selected but GROQ_API_KEY is not set in .env")
        return "groq"
    if provider == "ollama":
        if not _ollama_reachable():
            raise ValueError(
                f"Ollama not reachable at {settings.ollama_base_url}. "
                "Start Ollama and run: ollama pull llama3.2"
            )
        return "ollama"
    # auto
    if settings.llm_provider == "groq" and settings.has_groq:
        return "groq"
    if settings.llm_provider == "ollama" and _ollama_reachable():
        return "ollama"
    if settings.has_groq:
        return "groq"
    if _ollama_reachable():
        return "ollama"
    raise ValueError(
        "No LLM available. Set GROQ_API_KEY in .env or run Ollama locally "
        "(ollama pull llama3.2)."
    )


def get_chat_llm(provider: Provider = "auto", temperature: float = 0.2) -> BaseChatModel:
    active = _resolve_provider(provider)
    if active == "groq":
        return ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=temperature,
        )
    from langchain_community.chat_models import ChatOllama

    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=temperature,
    )
