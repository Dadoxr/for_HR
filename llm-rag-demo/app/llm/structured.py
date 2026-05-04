import json
import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.llm.router import LLMRouter

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

STRUCTURED_SYSTEM_PROMPT = """You must respond ONLY with valid JSON matching this schema:
{schema}

No markdown, no explanation - just the raw JSON object."""


async def generate_structured(
    router: LLMRouter,
    output_model: type[T],
    user_prompt: str,
    system_context: str = "",
    temperature: float = 0.0,
    max_retries: int = 2,
) -> T:
    """Generate a structured response validated against a Pydantic model.

    Sends the model's JSON schema as part of the system prompt,
    then parses and validates the LLM's JSON output.
    Retries with an error hint on validation failure.
    """
    schema_json = json.dumps(output_model.model_json_schema(), indent=2)
    system_msg = STRUCTURED_SYSTEM_PROMPT.format(schema=schema_json)
    if system_context:
        system_msg = f"{system_context}\n\n{system_msg}"

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_prompt},
    ]

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        response = await router.complete(
            messages=messages,
            temperature=temperature,
        )

        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        try:
            data = json.loads(raw)
            return output_model.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            logger.warning(
                "Structured output parse attempt %d/%d failed: %s",
                attempt,
                max_retries,
                exc,
            )
            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": f"Invalid JSON. Error: {exc}. Please fix and return only valid JSON.",
            })

    raise ValueError(
        f"Failed to get valid structured output after {max_retries} attempts: {last_error}"
    )
