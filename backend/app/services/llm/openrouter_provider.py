import httpx
from app.services.llm.base import LLMProvider


class OpenRouterProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.base_url = base_url

    async def _post(self, payload: dict) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def generate_text(self, messages, model: str, **kwargs) -> str:
        data = await self._post({"model": model, "messages": messages, **kwargs})
        return data["choices"][0]["message"]["content"]

    async def generate_json(self, messages, schema: dict, model: str, **kwargs) -> dict:
        payload = {
            "model": model,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "meeting_summary", "strict": True, "schema": schema},
            },
            **kwargs,
        }
        data = await self._post(payload)
        import json
        return json.loads(data["choices"][0]["message"]["content"])
