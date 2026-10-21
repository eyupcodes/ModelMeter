"""Tests for provider adapters using mocked HTTP responses."""

from __future__ import annotations

import httpx
import pytest

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


def _provider(monkeypatch, body) -> OpenAICompatibleProvider:
    monkeypatch.setenv("DUMMY_KEY", "secret-token")
    cfg = ProviderConfig(
        name="test",
        base_url="https://api.openai.com/v1",
        model="gpt-4o",
        api_key_env="DUMMY_KEY",
    )

    def mock_post(self, url, **kwargs):
        return httpx.Response(
            status_code=200, request=httpx.Request("POST", url), json=body
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    return OpenAICompatibleProvider(cfg)


@pytest.mark.parametrize(
    "body",
    [{}, {"choices": []}, [], {"choices": ["x"]}, {"choices": None}],
)
def test_reply_without_completion_raises(monkeypatch, body) -> None:
    with pytest.raises(ValueError, match="returned no completion"):
        _provider(monkeypatch, body).execute("hi")


def test_reply_error_message_is_included(monkeypatch) -> None:
    body = {"error": {"message": "quota exceeded"}}
    with pytest.raises(ValueError, match="quota exceeded"):
        _provider(monkeypatch, body).execute("hi")


def test_null_usage_and_content_are_tolerated(monkeypatch) -> None:
    body = {"choices": [{"message": {"content": None}}], "usage": None}
    resp = _provider(monkeypatch, body).execute("hi")
    assert resp.text == ""
    assert resp.input_tokens == resp.output_tokens == 0


def test_provider_without_api_key_env_sends_no_authorization(monkeypatch) -> None:
    cfg = ProviderConfig(
        name="ollama",
        base_url="http://localhost:11434/v1",
        model="llama3.2",
    )
    seen: dict = {}

    def mock_post(self, url, **kwargs):
        seen["url"] = url
        seen["headers"] = kwargs["headers"]
        return httpx.Response(
            status_code=200,
            request=httpx.Request("POST", url),
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    resp = get_provider_adapter(cfg).execute("hi")

    assert resp.text == "ok"
    assert seen["url"] == "http://localhost:11434/v1/chat/completions"
    assert "Authorization" not in seen["headers"]
