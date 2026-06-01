from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class LLMResponse:
    text: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class LLMService(Protocol):
    """
    Structural protocol for LLM service implementations.
    Both GeminiService and OpenAIService satisfy this protocol,
    allowing callers to swap providers without changing call sites.
    """

    def generate(
        self,
        prompt_name: str,
        prompt_version: str,
        variables: dict[str, Any],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> LLMResponse: ...

    async def generate_async(
        self,
        prompt_name: str,
        prompt_version: str,
        variables: dict[str, Any],
        *,
        model: str | None = None,
    ) -> LLMResponse: ...
