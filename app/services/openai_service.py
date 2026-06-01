import asyncio
from typing import Any

import openai

from app.core.config import Settings, get_settings
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import get_logger
from app.prompts.registry import PromptRegistry
from app.services.llm_base import LLMResponse

_logger = get_logger(__name__)


class OpenAIService:
    """
    Calls OpenAI Chat Completions API using a prompt rendered from the PromptRegistry.

    Config (via Settings / env):
        OPENAI_API_KEY           — required
        OPENAI_DEFAULT_MODEL     — default: gpt-4o
        OPENAI_TIMEOUT_SECONDS   — default: 60
    """

    def __init__(
        self,
        registry: PromptRegistry,
        settings: Settings | None = None,
    ) -> None:
        self._registry = registry
        self._settings = settings or get_settings()
        self._client: openai.OpenAI | None = (
            openai.OpenAI(
                api_key=self._settings.openai_api_key,
                timeout=self._settings.openai_timeout_seconds,
            )
            if self._settings.openai_api_key
            else None
        )

    def generate(
        self,
        prompt_name: str,
        prompt_version: str,
        variables: dict[str, Any],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        if not self._settings.openai_api_key:
            raise ServiceUnavailableError(
                "OpenAI API key is not configured. Set OPENAI_API_KEY in .env"
            )

        if self._client is None:
            raise ServiceUnavailableError(
                "OpenAI client is not initialized. Check the API key configuration."
            )
        client = self._client
        prompt_text = self._registry.render(prompt_name, prompt_version, variables)
        model_name = model or self._settings.openai_default_model

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt_text})

        _logger.info(
            "openai_call_start",
            prompt=prompt_name,
            version=prompt_version,
            model=model_name,
            has_system_prompt=system_prompt is not None,
        )

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,  # type: ignore[arg-type]
            )

            content = response.choices[0].message.content
            if content is None:
                raise ValueError("OpenAI returned empty content (possibly filtered)")

            usage = response.usage
            _logger.info(
                "openai_call_done",
                model=model_name,
                chars=len(content),
                prompt_tokens=usage.prompt_tokens if usage else None,
                completion_tokens=usage.completion_tokens if usage else None,
            )
            return LLMResponse(
                text=content,
                model=model_name,
                prompt_tokens=usage.prompt_tokens if usage else None,
                completion_tokens=usage.completion_tokens if usage else None,
            )

        except ServiceUnavailableError:
            raise
        except Exception as exc:
            _logger.error("openai_call_failed", error=str(exc), model=model_name)
            raise ServiceUnavailableError(
                message=f"OpenAI call failed: {exc}",
                details={"model": model_name, "prompt": prompt_name},
            ) from exc

    async def generate_async(
        self,
        prompt_name: str,
        prompt_version: str,
        variables: dict[str, Any],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Non-blocking wrapper for use in async FastAPI endpoints.
        Runs generate() in a thread pool so the event loop is never blocked."""
        return await asyncio.to_thread(
            self.generate,
            prompt_name, prompt_version, variables,
            model=model,
            system_prompt=system_prompt,
        )
