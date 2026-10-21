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


def _http_sequence(monkeypatch, statuses, headers=None):
    calls = []
    sleeps = []
    monkeypatch.setattr("modelmeter.providers.time.sleep", sleeps.append)

    def mock_post(self, url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(
            status_code=statuses[len(calls) - 1],
            request=httpx.Request("POST", url),
            headers=headers,
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    cfg = ProviderConfig(
        name="test", base_url="https://example.com/v1", model="test-model"
    )
    return OpenAICompatibleProvider(cfg), calls, sleeps


@pytest.mark.parametrize(
    ("retry_after", "delay"),
    [
        (None, 1.0),
        ("0", 0.0),
        ("2", 2.0),
        ("0.5", 0.5),
        ("30", 30.0),
        ("invalid", 1.0),
        ("-1", 1.0),
        ("NaN", 1.0),
        ("Infinity", 1.0),
        ("Wed, 21 Oct 2015 07:28:02 GMT", 2.0),
        ("Wed, 21 Oct 2015 07:28:02", 2.0),
        ("Wed, 21 Oct 2015 07:27:00 GMT", 0.0),
    ],
)
def test_rate_limit_retries_once_with_retry_after(monkeypatch, retry_after, delay):
    monkeypatch.setattr("modelmeter.providers.time.time", lambda: 1445412480.0)
    headers = {} if retry_after is None else {"Retry-After": retry_after}
    adapter, calls, sleeps = _http_sequence(monkeypatch, [429, 200], headers)
    clock = iter([10.0, 10.0 + delay + 0.25])
    monkeypatch.setattr("modelmeter.providers.time.perf_counter", lambda: next(clock))

    response = adapter.execute("hello")

    assert response.text == "ok"
    assert response.latency_ms == round((delay + 0.25) * 1000.0, 2)
    assert len(calls) == 2
    assert calls[0] == calls[1]
    assert sleeps == [delay]


@pytest.mark.parametrize("retry_status", [429, 401, 500])
def test_failed_retry_raises_without_a_third_attempt(monkeypatch, retry_status):
    adapter, calls, sleeps = _http_sequence(monkeypatch, [429, retry_status])

    with pytest.raises(httpx.HTTPStatusError) as exc:
        adapter.execute("hello")

    assert exc.value.response.status_code == retry_status
    assert len(calls) == 2
    assert sleeps == [1.0]


@pytest.mark.parametrize(
    "retry_after", ["31", "1e100", "Wed, 21 Oct 2015 07:29:00 GMT"]
)
def test_long_rate_limit_delay_is_not_retried(monkeypatch, retry_after):
    monkeypatch.setattr("modelmeter.providers.time.time", lambda: 1445412480.0)
    adapter, calls, sleeps = _http_sequence(
        monkeypatch, [429], {"Retry-After": retry_after}
    )

    with pytest.raises(httpx.HTTPStatusError) as exc:
        adapter.execute("hello")

    assert exc.value.response.status_code == 429
    assert len(calls) == 1
    assert sleeps == []


@pytest.mark.parametrize("status", [400, 401, 403, 404, 500, 503])
def test_other_http_errors_are_not_retried(monkeypatch, status):
    adapter, calls, sleeps = _http_sequence(monkeypatch, [status])

    with pytest.raises(httpx.HTTPStatusError) as exc:
        adapter.execute("hello")

    assert exc.value.response.status_code == status
    assert len(calls) == 1
    assert sleeps == []


def test_network_failure_is_not_retried(monkeypatch):
    adapter, calls, sleeps = _http_sequence(monkeypatch, [])

    def mock_post(self, url, **kwargs):
        calls.append((url, kwargs))
        raise httpx.ConnectError(
            "connection refused", request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    with pytest.raises(httpx.ConnectError, match="connection refused"):
        adapter.execute("hello")

    assert len(calls) == 1
    assert sleeps == []


def test_successful_request_does_not_retry_or_sleep(monkeypatch):
    adapter, calls, sleeps = _http_sequence(monkeypatch, [200])

    assert adapter.execute("hello").text == "ok"
    assert len(calls) == 1
    assert sleeps == []
