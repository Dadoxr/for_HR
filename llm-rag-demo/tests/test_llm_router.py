import pytest

from app.llm.router import LLMRouter
from tests.conftest import MockProvider


@pytest.mark.asyncio
async def test_router_uses_first_healthy_provider(mock_provider):
    router = LLMRouter(providers=[mock_provider])
    result = await router.complete(messages=[{"role": "user", "content": "hi"}])

    assert result.provider == "primary"
    assert mock_provider.call_count == 1


@pytest.mark.asyncio
async def test_router_falls_back_on_failure(failing_provider, mock_provider):
    backup = MockProvider(name="backup", response="backup response")
    router = LLMRouter(
        providers=[failing_provider, backup],
        max_retries=1,
    )
    result = await router.complete(messages=[{"role": "user", "content": "hi"}])

    assert result.provider == "backup"
    assert result.content == "backup response"
    assert failing_provider.call_count == 1
    assert backup.call_count == 1


@pytest.mark.asyncio
async def test_router_retries_before_fallback():
    flaky = MockProvider(name="flaky", should_fail=True)
    backup = MockProvider(name="backup")
    router = LLMRouter(providers=[flaky, backup], max_retries=3)

    result = await router.complete(messages=[{"role": "user", "content": "hi"}])

    assert flaky.call_count == 3
    assert result.provider == "backup"


@pytest.mark.asyncio
async def test_router_raises_when_all_fail():
    p1 = MockProvider(name="a", should_fail=True)
    p2 = MockProvider(name="b", should_fail=True)
    router = LLMRouter(providers=[p1, p2], max_retries=1)

    with pytest.raises(RuntimeError, match="All LLM providers failed"):
        await router.complete(messages=[{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_health_tracking_marks_unhealthy(failing_provider):
    backup = MockProvider(name="backup")
    router = LLMRouter(providers=[failing_provider, backup], max_retries=1)

    await router.complete(messages=[{"role": "user", "content": "first"}])
    health = router.get_health("failing")
    assert health.consecutive_failures > 0
    assert not health.is_healthy


@pytest.mark.asyncio
async def test_health_resets_on_success(mock_provider):
    router = LLMRouter(providers=[mock_provider])
    router.get_health("primary").record_failure()

    router.get_health("primary").cooldown_seconds = 0
    await router.complete(messages=[{"role": "user", "content": "hi"}])

    assert router.get_health("primary").consecutive_failures == 0
