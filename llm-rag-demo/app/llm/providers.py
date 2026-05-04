import abc
import time
from dataclasses import dataclass, field

import httpx


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    usage: dict = field(default_factory=dict)
    latency_ms: float = 0.0


class LLMProvider(abc.ABC):
    name: str

    @abc.abstractmethod
    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        ...


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, default_model: str = "gpt-4o-mini"):
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)
        self._default_model = default_model

    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        start = time.monotonic()
        resp = await self._client.chat.completions.create(
            model=model or self._default_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency = (time.monotonic() - start) * 1000
        choice = resp.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            provider=self.name,
            model=resp.model,
            usage={
                "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
            },
            latency_ms=latency,
        )


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, default_model: str = "claude-sonnet-4-20250514"):
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=api_key)
        self._default_model = default_model

    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        system_msg = ""
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                chat_messages.append(m)

        start = time.monotonic()
        resp = await self._client.messages.create(
            model=model or self._default_model,
            system=system_msg or "You are a helpful assistant.",
            messages=chat_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency = (time.monotonic() - start) * 1000
        content = resp.content[0].text if resp.content else ""
        return LLMResponse(
            content=content,
            provider=self.name,
            model=resp.model,
            usage={
                "prompt_tokens": resp.usage.input_tokens,
                "completion_tokens": resp.usage.output_tokens,
            },
            latency_ms=latency,
        )


class OpenRouterProvider(LLMProvider):
    name = "openrouter"

    def __init__(self, api_key: str, default_model: str = "openai/gpt-4o-mini"):
        self._api_key = api_key
        self._default_model = default_model
        self._base_url = "https://openrouter.ai/api/v1"

    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model or self._default_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            resp.raise_for_status()

        latency = (time.monotonic() - start) * 1000
        data = resp.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return LLMResponse(
            content=choice["message"]["content"],
            provider=self.name,
            model=data.get("model", model or self._default_model),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            },
            latency_ms=latency,
        )
