import asyncio
import os
from typing import Type, TypeVar

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

_client = anthropic.AsyncAnthropic()
MODEL = "claude-haiku-4-5-20251001"
MAX_RETRIES = 3


async def query(system: str, user: str, output_model: Type[T]) -> T:
    """
    Call Claude and coerce the response into output_model via tool_use.

    Uses tool_choice={"type": "tool"} to guarantee structured JSON output.
    Retries up to MAX_RETRIES times with exponential backoff (1s, 2s, 4s).
    Raises the last exception if all attempts fail.
    """
    tool = {
        "name": "output",
        "description": "Return the structured output for this task.",
        "input_schema": output_model.model_json_schema(),
    }

    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            response = await _client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user}],
                tools=[tool],
                tool_choice={"type": "tool", "name": "output"},
            )
            tool_block = next(b for b in response.content if b.type == "tool_use")
            return output_model.model_validate(tool_block.input)
        except anthropic.RateLimitError as exc:
            last_exc = exc
            if attempt < MAX_RETRIES - 1:
                wait = _rate_limit_wait(exc)
                print(f"  [rate limit] waiting {wait}s before retry {attempt + 1}/{MAX_RETRIES}...")
                await asyncio.sleep(wait)
        except Exception as exc:
            last_exc = exc
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2**attempt)

    raise last_exc


def _rate_limit_wait(exc: anthropic.RateLimitError) -> int:
    """Return seconds to wait before retrying a rate-limited request.

    Prefers the retry-after header returned by the API; falls back to 60s.
    """
    try:
        retry_after = exc.response.headers.get("retry-after")
        if retry_after:
            return int(retry_after) + 1  # +1s buffer
    except Exception:
        pass
    return 60
