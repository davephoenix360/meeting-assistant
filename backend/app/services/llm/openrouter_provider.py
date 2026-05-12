import asyncio
import json
import random

import httpx
from app.services.llm.base import LLMProvider, LLMProviderError


class OpenRouterProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.base_url = base_url

    async def _post(self, payload: dict) -> dict:
        if not self.api_key:
            raise LLMProviderError(
                "OpenRouter API key is missing", status_code=401, provider="openrouter"
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Be conservative with retries: free-tier models can rate limit frequently.
        max_retries = 3
        base_delay = 1.0
        max_delay = 10.0

        async with httpx.AsyncClient(timeout=60) as client:
            for attempt in range(max_retries + 1):
                try:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as e:
                    status = e.response.status_code if e.response is not None else None

                    # Retry rate limiting with backoff.
                    if status == 429 and attempt < max_retries:
                        retry_after = (
                            e.response.headers.get("retry-after")
                            if e.response is not None
                            else None
                        )
                        delay: float
                        if retry_after and retry_after.isdigit():
                            delay = float(retry_after)
                        else:
                            delay = min(max_delay, base_delay * (2**attempt))
                            delay = delay * (0.8 + random.random() * 0.4)  # jitter
                        await asyncio.sleep(delay)
                        continue

                    detail = None
                    try:
                        detail = e.response.text
                    except Exception:
                        detail = str(e)

                    raise LLMProviderError(
                        f"OpenRouter request failed ({status}): {detail}",
                        status_code=status,
                        provider="openrouter",
                    )
                except httpx.RequestError as e:
                    raise LLMProviderError(
                        f"OpenRouter request error: {e}",
                        status_code=503,
                        provider="openrouter",
                    )

    async def generate_text(self, messages, model: str, **kwargs) -> str:
        data = await self._post({"model": model, "messages": messages, **kwargs})
        return data["choices"][0]["message"]["content"]

    async def generate_json(self, messages, schema: dict, model: str, **kwargs) -> dict:
        payload = {
            "model": model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "meeting_summary",
                    "strict": True,
                    "schema": schema,
                },
            },
            **kwargs,
        }
        data = await self._post(payload)
        try:
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as e:
            raise LLMProviderError(
                f"OpenRouter returned invalid JSON content: {e}",
                status_code=502,
                provider="openrouter",
            )
