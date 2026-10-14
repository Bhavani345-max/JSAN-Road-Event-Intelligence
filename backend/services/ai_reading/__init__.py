"""Reads articles with a language model (OpenRouter) and checks the answers against them."""

from .client import AiError, ChatResult, OpenRouterClient, parse_json_answer
from .reading import (
    FULL,
    TRIAGE,
    AiConfig,
    ArticleText,
    contains,
    full_prompt,
    normalise,
    read_full_answer,
    read_triage_answer,
    triage_prompt,
)

__all__ = [
    "FULL",
    "TRIAGE",
    "AiConfig",
    "AiError",
    "ArticleText",
    "ChatResult",
    "OpenRouterClient",
    "contains",
    "full_prompt",
    "normalise",
    "parse_json_answer",
    "read_full_answer",
    "read_triage_answer",
    "triage_prompt",
]
