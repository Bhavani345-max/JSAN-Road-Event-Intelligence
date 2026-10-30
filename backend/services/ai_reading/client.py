"""A small chat client that asks for, and parses, a JSON answer.

Made for OpenRouter; any OpenAI-compatible API works through its base URL (NVIDIA
NIM since 30 October 2026). The key, the model and its fallbacks come from
configuration (see the API's settings); nothing here names a model. The answer
is untrusted: callers check it against the article before using any of it
(reading.py).
"""

import json
import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER = "OpenRouter"
# Known providers by host, for messages and logs; any other is named by its host.
_PROVIDERS = {"openrouter.ai": OPENROUTER, "integrate.api.nvidia.com": "NVIDIA NIM"}


def provider_name(base_url: str) -> str:
    """Who answers at `base_url`, as messages and logs name it."""
    host = (urlsplit(base_url).hostname or "").lower()
    return _PROVIDERS.get(host, host or "the AI service")
# Answers worth waiting for and asking again: rate limits, overloaded or
# unavailable upstream providers, gateway timeouts.
_RETRY_STATUSES = {408, 429, 500, 502, 503, 504}


class AiError(Exception):
    """The model could not be asked, or did not answer with JSON."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass
class ChatResult:
    content: dict
    # The model that actually answered (a fallback, when the first was busy).
    model: str
    usage: dict = field(default_factory=dict)


_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def parse_json_answer(text: str | None) -> dict:
    """The JSON object in a model's answer, tolerating code fences and stray text."""
    if not text or not text.strip():
        raise AiError("The model returned an empty answer.", retryable=True)
    cleaned = _FENCE.sub("", text.strip())
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise AiError("The model's answer is not JSON.", retryable=True) from None
        try:
            value = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as error:
            raise AiError(f"The model's answer is not valid JSON: {error}", retryable=True) from None
    if not isinstance(value, dict):
        raise AiError("The model's answer is not a JSON object.", retryable=True)
    return value


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        fallback_models: list[str] | None = None,
        base_url: str = DEFAULT_BASE_URL,
        reasoning: bool = True,
        disable_thinking: bool = False,
        timeout_seconds: float = 240,
        retries: int = 2,
        retry_delays: tuple[float, ...] = (20, 60),
        app_name: str = "JSAN Road Event Intelligence",
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise ValueError("An API key for AI reading is required.")
        self.provider = provider_name(base_url)
        self.model = model
        self.fallback_models = [m for m in (fallback_models or []) if m and m != model]
        self._reasoning = reasoning
        self._disable_thinking = disable_thinking
        self._retries = retries
        self._retry_delays = retry_delays
        self._sleep = sleep
        self._http = httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
            transport=transport,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-Title": app_name,
            },
        )
        # Requests the model answered. Rate-limited or failed requests do not
        # count against an OpenRouter key's free daily requests, so are not counted.
        self.requests_sent = 0
        # Every request sent, answered or not.
        self.attempts = 0

    def close(self) -> None:
        self._http.close()

    def free_requests_remaining(self) -> int | None:
        """Free-model requests the key has left today, or None if not known.

        Only OpenRouter says (its /key); other providers are not asked."""
        if self.provider != OPENROUTER:
            return None
        try:
            response = self._http.get("/key", timeout=30)
            response.raise_for_status()
            data = response.json().get("data") or {}
        except (httpx.HTTPError, ValueError):
            return None
        free = data.get("free_model_daily_requests") or {}
        remaining = free.get("remaining")
        return int(remaining) if isinstance(remaining, int | float) else None

    def chat_json(self, system: str, user: str, *, max_tokens: int) -> ChatResult:
        """Ask once (with retries on busy upstreams) and return the parsed JSON answer."""
        body: dict = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": max_tokens,
            "temperature": 0,
        }
        if self.fallback_models:
            body["models"] = [self.model, *self.fallback_models]
        else:
            body["model"] = self.model
        if self._reasoning:
            body["reasoning"] = {"enabled": True}
        if self._disable_thinking:
            # NVIDIA NIM's chat template option: a model that thinks by default
            # (Nemotron) answers at once, instead of spending max_tokens thinking.
            body["chat_template_kwargs"] = {"enable_thinking": False}

        attempt = 0
        while True:
            try:
                return self._send(body)
            except AiError as error:
                if not error.retryable or attempt >= self._retries:
                    raise
                delay = self._retry_delays[min(attempt, len(self._retry_delays) - 1)]
                logger.info("AI reading: %s Asking again in %.0f s.", error, delay)
                self._sleep(delay)
                attempt += 1

    def _send(self, body: dict) -> ChatResult:
        self.attempts += 1
        try:
            response = self._http.post("/chat/completions", json=body)
        except httpx.TimeoutException:
            raise AiError("The model did not answer in time.", retryable=True) from None
        except httpx.HTTPError as error:
            raise AiError(f"{self.provider} could not be reached: {error}", retryable=True) from None

        if response.status_code != 200:
            raise AiError(
                f"{self.provider} answered {response.status_code}: {_error_message(response)}",
                retryable=response.status_code in _RETRY_STATUSES,
            )
        self.requests_sent += 1
        try:
            payload = response.json()
        except ValueError:
            raise AiError(f"{self.provider}'s reply is not JSON.", retryable=True) from None
        # OpenRouter can return 200 with an error object when the provider failed mid-way.
        if payload.get("error"):
            error = payload["error"]
            code = error.get("code") if isinstance(error, dict) else None
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise AiError(f"The model failed: {message}", retryable=code in _RETRY_STATUSES)
        choices = payload.get("choices") or []
        if not choices:
            raise AiError("The model returned no answer.", retryable=True)
        message = choices[0].get("message") or {}
        if choices[0].get("finish_reason") == "length" and not (message.get("content") or "").rstrip().endswith("}"):
            raise AiError(
                "The model's answer was cut off at the token limit (raise max_tokens or lower batch_size).",
                retryable=True,
            )
        return ChatResult(
            content=parse_json_answer(message.get("content")),
            model=payload.get("model") or body.get("model") or self.model,
            usage=payload.get("usage") or {},
        )


def _error_message(response: httpx.Response) -> str:
    try:
        error = response.json().get("error") or {}
    except ValueError:
        return response.text[:200]
    message = error.get("message") or ""
    raw = (error.get("metadata") or {}).get("raw")
    if isinstance(raw, str) and raw:
        message = f"{message} ({raw[:200]})"
    return message or response.text[:200]
