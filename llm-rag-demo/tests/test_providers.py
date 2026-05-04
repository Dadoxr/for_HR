"""Tests for real provider classes with mocked SDK/HTTP calls."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.providers import (
    AnthropicProvider,
    OpenAIProvider,
    OpenRouterProvider,
)


# --- OpenAI Provider ---


@pytest.mark.asyncio
async def test_openai_provider_complete():
    mock_choice = MagicMock()
    mock_choice.message.content = "Hello from OpenAI"

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 10
    mock_usage.completion_tokens = 5

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.model = "gpt-4o-mini"
    mock_response.usage = mock_usage

    with patch("openai.AsyncOpenAI") as MockClient:
        instance = MockClient.return_value
        instance.chat.completions.create = AsyncMock(return_value=mock_response)

        provider = OpenAIProvider(api_key="sk-test", default_model="gpt-4o-mini")
        result = await provider.complete(
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.5,
            max_tokens=100,
        )

    assert result.content == "Hello from OpenAI"
    assert result.provider == "openai"
    assert result.model == "gpt-4o-mini"
    assert result.usage["prompt_tokens"] == 10
    assert result.usage["completion_tokens"] == 5
    assert result.latency_ms > 0

    instance.chat.completions.create.assert_called_once_with(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
        temperature=0.5,
        max_tokens=100,
    )


@pytest.mark.asyncio
async def test_openai_provider_empty_content():
    mock_choice = MagicMock()
    mock_choice.message.content = None

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.model = "gpt-4o-mini"
    mock_response.usage = None

    with patch("openai.AsyncOpenAI") as MockClient:
        instance = MockClient.return_value
        instance.chat.completions.create = AsyncMock(return_value=mock_response)

        provider = OpenAIProvider(api_key="sk-test")
        result = await provider.complete(messages=[{"role": "user", "content": "hi"}])

    assert result.content == ""
    assert result.usage["prompt_tokens"] == 0


@pytest.mark.asyncio
async def test_openai_provider_uses_custom_model():
    mock_choice = MagicMock()
    mock_choice.message.content = "ok"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.model = "gpt-4o"
    mock_response.usage = MagicMock(prompt_tokens=1, completion_tokens=1)

    with patch("openai.AsyncOpenAI") as MockClient:
        instance = MockClient.return_value
        instance.chat.completions.create = AsyncMock(return_value=mock_response)

        provider = OpenAIProvider(api_key="sk-test", default_model="gpt-4o-mini")
        await provider.complete(
            messages=[{"role": "user", "content": "hi"}],
            model="gpt-4o",
        )

    instance.chat.completions.create.assert_called_once()
    call_kwargs = instance.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-4o"


# --- Anthropic Provider ---


@pytest.mark.asyncio
async def test_anthropic_provider_complete():
    mock_block = MagicMock()
    mock_block.text = "Hello from Anthropic"

    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.model = "claude-sonnet-4-20250514"
    mock_response.usage = MagicMock(input_tokens=12, output_tokens=8)

    with patch("anthropic.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create = AsyncMock(return_value=mock_response)

        provider = AnthropicProvider(api_key="sk-ant-test")
        result = await provider.complete(
            messages=[
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "hi"},
            ],
        )

    assert result.content == "Hello from Anthropic"
    assert result.provider == "anthropic"
    assert result.usage["prompt_tokens"] == 12
    assert result.usage["completion_tokens"] == 8

    instance.messages.create.assert_called_once()
    call_kwargs = instance.messages.create.call_args[1]
    assert call_kwargs["system"] == "You are helpful."
    assert call_kwargs["messages"] == [{"role": "user", "content": "hi"}]


@pytest.mark.asyncio
async def test_anthropic_provider_no_system_message():
    mock_block = MagicMock()
    mock_block.text = "reply"
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.model = "claude-sonnet-4-20250514"
    mock_response.usage = MagicMock(input_tokens=5, output_tokens=3)

    with patch("anthropic.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create = AsyncMock(return_value=mock_response)

        provider = AnthropicProvider(api_key="sk-ant-test")
        await provider.complete(messages=[{"role": "user", "content": "hi"}])

    call_kwargs = instance.messages.create.call_args[1]
    assert call_kwargs["system"] == "You are a helpful assistant."


@pytest.mark.asyncio
async def test_anthropic_provider_empty_content():
    mock_response = MagicMock()
    mock_response.content = []
    mock_response.model = "claude-sonnet-4-20250514"
    mock_response.usage = MagicMock(input_tokens=5, output_tokens=0)

    with patch("anthropic.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create = AsyncMock(return_value=mock_response)

        provider = AnthropicProvider(api_key="sk-ant-test")
        result = await provider.complete(messages=[{"role": "user", "content": "hi"}])

    assert result.content == ""


# --- OpenRouter Provider ---


@pytest.mark.asyncio
async def test_openrouter_provider_complete():
    mock_json = {
        "choices": [{"message": {"content": "Hello from OpenRouter"}}],
        "model": "openai/gpt-4o-mini",
        "usage": {"prompt_tokens": 15, "completion_tokens": 7},
    }

    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_json
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockHttpx:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        MockHttpx.return_value = mock_client

        provider = OpenRouterProvider(api_key="sk-or-test")
        result = await provider.complete(
            messages=[{"role": "user", "content": "hi"}],
        )

    assert result.content == "Hello from OpenRouter"
    assert result.provider == "openrouter"
    assert result.usage["prompt_tokens"] == 15

    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "Bearer sk-or-test" in call_args[1]["headers"]["Authorization"]


@pytest.mark.asyncio
async def test_openrouter_provider_http_error():
    import httpx

    with patch("httpx.AsyncClient") as MockHttpx:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "429 Too Many Requests",
            request=MagicMock(),
            response=MagicMock(status_code=429),
        )
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        MockHttpx.return_value = mock_client

        provider = OpenRouterProvider(api_key="sk-or-test")
        with pytest.raises(httpx.HTTPStatusError):
            await provider.complete(messages=[{"role": "user", "content": "hi"}])
