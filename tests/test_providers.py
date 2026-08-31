"""Tests for provider adapters using mocked HTTP responses."""

from __future__ import annotations

import pytest
import httpx

from modelmeter.config import ProviderConfig
from modelmeter.providers import (
    OpenAICompatibleProvider,
    get_provider_adapter,
)


def test_factory_openai_compatible() -> None:
    cfg = ProviderConfig(
        name="test",
        base_url="https://api.openai.com/v1",
        model="gpt-4o",
        api_key_env="TEST_API_KEY",
    )
    adapter = get_provider_adapter(cfg)
    assert isinstance(adapter, OpenAICompatibleProvider)


def test_missing_api_key_raises(monkeypatch) -> None:
    monkeypatch.delenv("MISSING_KEY_VAR", raising=False)
    cfg = ProviderConfig(
        name="test",
        base_url="https://api.openai.com/v1",
        model="gpt-4o",
        api_key_env="MISSING_KEY_VAR",
    )
    adapter = get_provider_adapter(cfg)
    with pytest.raises(ValueError, match="Missing environment variable"):
        adapter.execute("hello")


def test_mocked_openai_response(monkeypatch) -> None:
    monkeypatch.setenv("DUMMY_KEY", "secret-token")
    cfg = ProviderConfig(
        name="test",
        base_url="https://api.openai.com/v1",
        model="gpt-4o",
        api_key_env="DUMMY_KEY",
    )
    adapter = get_provider_adapter(cfg)

    def mock_post(self, url, **kwargs):
        assert "Authorization" in kwargs["headers"]
        assert kwargs["json"]["model"] == "gpt-4o"
        req = httpx.Request("POST", url)
        return httpx.Response(
            status_code=200,
            request=req,
            json={
                "choices": [{"message": {"content": "4"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 1},
            },
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    resp = adapter.execute("What is 2+2?")
    assert resp.text == "4"
    assert resp.input_tokens == 5
    assert resp.output_tokens == 1
    assert resp.latency_ms >= 0.0
