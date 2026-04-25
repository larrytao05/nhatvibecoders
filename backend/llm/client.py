import asyncio
from typing import Type, TypeVar

import anthropic
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

_client = anthropic.AsyncAnthropic()
MODEL = "claude-sonnet-4-6"
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
        except Exception as exc:
            last_exc = exc
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2**attempt)

    raise last_exc
