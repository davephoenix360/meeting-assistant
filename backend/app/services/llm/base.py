from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def generate_text(self, messages, model: str, **kwargs) -> str: ...

    @abstractmethod
    async def generate_json(self, messages, schema: dict, model: str, **kwargs) -> dict: ...
