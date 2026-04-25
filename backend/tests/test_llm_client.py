"""Isolation tests for llm/client.py — the query() wrapper."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from llm.client import MAX_RETRIES, query
from llm.schemas import WeeklyPlan


# Minimal valid WeeklyPlan payload (all rest days except Monday).
_VALID_PLAN_INPUT = {
    "schedule": [
        {"day": "Monday",    "muscle_groups": ["Upper Chest"], "reasoning": "Push"},
        {"day": "Tuesday",   "muscle_groups": [],              "reasoning": "Rest"},
        {"day": "Wednesday", "muscle_groups": [],              "reasoning": "Rest"},
        {"day": "Thursday",  "muscle_groups": [],              "reasoning": "Rest"},
        {"day": "Friday",    "muscle_groups": [],              "reasoning": "Rest"},
        {"day": "Saturday",  "muscle_groups": [],              "reasoning": "Rest"},
        {"day": "Sunday",    "muscle_groups": [],              "reasoning": "Rest"},
    ]
}


def _mock_response(data: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.input = data
    resp = MagicMock()
    resp.content = [block]
    return resp


# ── Success ───────────────────────────────────────────────────────────────────

async def test_query_returns_validated_pydantic_model():
    with patch("llm.client._client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=_mock_response(_VALID_PLAN_INPUT))
        result = await query("sys", "usr", WeeklyPlan)

    assert isinstance(result, WeeklyPlan)
    assert len(result.schedule) == 7
    assert result.schedule[0].day == "Monday"
    assert result.schedule[0].muscle_groups == ["Upper Chest"]


async def test_query_uses_tool_use_with_correct_schema():
    with patch("llm.client._client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=_mock_response(_VALID_PLAN_INPUT))
        await query("sys", "usr", WeeklyPlan)

    kwargs = mock_client.messages.create.call_args.kwargs
    assert kwargs["tool_choice"] == {"type": "tool", "name": "output"}
    assert kwargs["tools"][0]["name"] == "output"
    assert "properties" in kwargs["tools"][0]["input_schema"]


async def test_query_passes_system_and_user_messages():
    with patch("llm.client._client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=_mock_response(_VALID_PLAN_INPUT))
        await query("my system prompt", "my user prompt", WeeklyPlan)

    kwargs = mock_client.messages.create.call_args.kwargs
    assert kwargs["system"] == "my system prompt"
    assert kwargs["messages"][0]["content"] == "my user prompt"


# ── Retry logic ───────────────────────────────────────────────────────────────

async def test_query_retries_max_times_then_raises():
    with patch("llm.client._client") as mock_client, \
         patch("asyncio.sleep", new=AsyncMock()):
        mock_client.messages.create = AsyncMock(side_effect=RuntimeError("API down"))

        with pytest.raises(RuntimeError, match="API down"):
            await query("sys", "usr", WeeklyPlan)

        assert mock_client.messages.create.call_count == MAX_RETRIES


async def test_query_exponential_backoff_delays():
    with patch("llm.client._client") as mock_client, \
         patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
        mock_client.messages.create = AsyncMock(side_effect=RuntimeError("fail"))

        with pytest.raises(RuntimeError):
            await query("sys", "usr", WeeklyPlan)

        # Between attempt 0→1: sleep(2^0=1), between 1→2: sleep(2^1=2)
        sleep_args = [c.args[0] for c in mock_sleep.call_args_list]
        assert sleep_args == [1, 2]


async def test_query_succeeds_on_third_attempt():
    resp = _mock_response(_VALID_PLAN_INPUT)
    side_effects = [RuntimeError("fail"), RuntimeError("fail"), resp]

    with patch("llm.client._client") as mock_client, \
         patch("asyncio.sleep", new=AsyncMock()):
        mock_client.messages.create = AsyncMock(side_effect=side_effects)
        result = await query("sys", "usr", WeeklyPlan)

    assert isinstance(result, WeeklyPlan)
    assert mock_client.messages.create.call_count == 3


async def test_query_no_sleep_after_last_attempt():
    with patch("llm.client._client") as mock_client, \
         patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
        mock_client.messages.create = AsyncMock(side_effect=RuntimeError("fail"))

        with pytest.raises(RuntimeError):
            await query("sys", "usr", WeeklyPlan)

        # MAX_RETRIES=3 → sleep only between attempts 0→1 and 1→2 (2 sleeps total)
        assert mock_sleep.call_count == MAX_RETRIES - 1
