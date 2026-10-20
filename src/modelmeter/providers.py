"""Provider adapters for LLM APIs.

All adapters implement the BaseProvider interface.
For V1, OpenAICompatibleProvider handles any standard OpenAI-compatible
chat completion endpoint (OpenAI, Groq, Mistral, local vLLM, etc.).
"""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod

import httpx
from pydantic import BaseModel

from modelmeter.config import ProviderConfig


class ProviderResponse(BaseModel):
    """Raw response returned by a provider adapter."""

    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: float


class BaseProvider(ABC):
    """Abstract interface for LLM provider adapters."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @abstractmethod
    def execute(self, prompt: str) -> ProviderResponse:
        """Send a prompt and return the parsed response."""
        raise NotImplementedError


def _completion_text(data: object, provider_name: str) -> str:
    """Return the first choice's text or raise if the reply has no completion."""
    choices = data.get("choices") if isinstance(data, dict) else None
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        detail = ""
        if isinstance(data, dict) and isinstance(data.get("error"), dict):
            detail = f": {data['error'].get('message', data['error'])}"
        raise ValueError(f"Provider {provider_name!r} returned no completion{detail}")
    message = choices[0].get("message") or {}
    return message.get("content") or ""


class OpenAICompatibleProvider(BaseProvider):
    """Adapter for standard OpenAI /v1/chat/completions endpoints."""

    def execute(self, prompt: str) -> ProviderResponse:
        api_key = os.environ.get(self.config.api_key_env)
        if not api_key:
            raise ValueError(
                f"Missing environment variable {self.config.api_key_env!r} "
                f"for provider {self.config.name!r}"
            )

        url = self.config.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
        }

        start_time = time.perf_counter()
        with httpx.Client(timeout=self.config.timeout_seconds) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        content = _completion_text(data, self.config.name)

        usage = data.get("usage") or {}
        in_tokens = usage.get("prompt_tokens", 0)
        out_tokens = usage.get("completion_tokens", 0)

        return ProviderResponse(
            text=content.strip(),
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            latency_ms=round(latency_ms, 2),
        )


def get_provider_adapter(config: ProviderConfig) -> BaseProvider:
    """Factory for instantiating provider adapters from config."""
    if config.kind == "openai-compatible":
        return OpenAICompatibleProvider(config)
    raise ValueError(f"Unsupported provider kind: {config.kind}")
