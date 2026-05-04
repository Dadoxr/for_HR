import asyncio
import logging
import time
from dataclasses import dataclass, field

from app.llm.providers import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class ProviderHealth:
    consecutive_failures: int = 0
    last_failure_time: float = 0.0
    cooldown_seconds: float = 60.0

    @property
    def is_healthy(self) -> bool:
        if self.consecutive_failures == 0:
            return True
        elapsed = time.monotonic() - self.last_failure_time
        return elapsed > self.cooldown_seconds

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        self.last_failure_time = time.monotonic()
        self.cooldown_seconds = min(300.0, 60.0 * (2 ** (self.consecutive_failures - 1)))

    def record_success(self) -> None:
        self.consecutive_failures = 0


class LLMRouter:
    """Multi-provider fallback router with health tracking.

    Tries providers in order. On failure (rate limit, timeout, API error),
    falls back to the next healthy provider.
    """

    def __init__(
        self,
        providers: list[LLMProvider],
        max_retries: int = 2,
        timeout: float = 30.0,
    ):
        self._providers = providers
        self._max_retries = max_retries
        self._timeout = timeout
        self._health: dict[str, ProviderHealth] = {
            p.name: ProviderHealth() for p in providers
        }

    @property
    def providers(self) -> list[LLMProvider]:
        return self._providers

    def get_health(self, provider_name: str) -> ProviderHealth:
        return self._health[provider_name]

    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        errors: list[tuple[str, Exception]] = []

        for provider in self._providers:
            health = self._health[provider.name]
            if not health.is_healthy:
                logger.info("Skipping %s (unhealthy, cooldown)", provider.name)
                continue

            for attempt in range(1, self._max_retries + 1):
                try:
                    response = await asyncio.wait_for(
                        provider.complete(
                            messages=messages,
                            model=model,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        ),
                        timeout=self._timeout,
                    )
                    health.record_success()
                    return response

                except Exception as exc:
                    logger.warning(
                        "Provider %s attempt %d/%d failed: %s",
                        provider.name,
                        attempt,
                        self._max_retries,
                        exc,
                    )
                    errors.append((provider.name, exc))

                    if attempt < self._max_retries:
                        await asyncio.sleep(0.5 * attempt)

            health.record_failure()
            logger.error("Provider %s exhausted retries, marking unhealthy", provider.name)

        raise RuntimeError(
            f"All LLM providers failed. Errors: "
            + "; ".join(f"{name}: {err}" for name, err in errors)
        )
