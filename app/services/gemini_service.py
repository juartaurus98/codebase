from typing import Any

from google import genai
from google.genai import types as genai_types

from app.core.config import Settings, get_settings
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import get_logger
from app.prompts.registry import PromptRegistry
from app.services.llm_base import LLMResponse

_logger = get_logger(__name__)


class GeminiService:
    """
    Calls Google Gemini API using a prompt rendered from the PromptRegistry.

    Config (via Settings / env):
        GEMINI_API_KEY           — required
        GEMINI_DEFAULT_MODEL     — default: gemini-2.0-flash
        GEMINI_TIMEOUT_SECONDS   — default: 60
    """

    def __init__(
        self,
        registry: PromptRegistry,
        settings: Settings | None = None,
    ) -> None:
        self._registry = registry
        self._settings = settings or get_settings()
        self._client: genai.Client | None = (
            genai.Client(api_key=self._settings.gemini_api_key)
            if self._settings.gemini_api_key
            else None
        )

    def _get_client(self) -> genai.Client:
        if self._client is None:
            raise ServiceUnavailableError(
                "Gemini API key is not configured. Set GEMINI_API_KEY in .env"
            )
        return self._client

    def _prepare(
        self,
        prompt_name: str,
        prompt_version: str,
        variables: dict[str, Any],
        model: str | None,
    ) -> tuple[str, str]:
        """Render the prompt and resolve model name, then log the call start."""
        prompt_text = self._registry.render(prompt_name, prompt_version, variables)
        model_name = model or self._settings.gemini_default_model
        _logger.info(
            "gemini_call_start",
            prompt=prompt_name,
            version=prompt_version,
            model=model_name,
        )
        return prompt_text, model_name

    def _build_response(
        self,
        response: genai_types.GenerateContentResponse,
        model_name: str,
    ) -> LLMResponse:
        # .text raises ValueError if the response was blocked by safety filters
        text: str = response.text
        usage = response.usage_metadata
        _logger.info(
            "gemini_call_done",
            model=model_name,
            chars=len(text),
            prompt_tokens=usage.prompt_token_count if usage else None,
            candidates_tokens=usage.candidates_token_count if usage else None,
        )
        return LLMResponse(
            text=text,
            model=model_name,
            prompt_tokens=usage.prompt_token_count if usage else None,
            completion_tokens=usage.candidates_token_count if usage else None,
        )

    def generate(
        self,
        prompt_name: str,
        prompt_version: str,
        variables: dict[str, Any],
        *,
        model: str | None = None,
    ) -> LLMResponse:
        client = self._get_client()
        prompt_text, model_name = self._prepare(
            prompt_name, prompt_version, variables, model
        )
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt_text,
            )
            return self._build_response(response, model_name)
        except ServiceUnavailableError:
            raise
        except Exception as exc:
            _logger.error("gemini_call_failed", error=str(exc), model=model_name)
            raise ServiceUnavailableError(
                message=f"Gemini call failed: {exc}",
                details={"model": model_name, "prompt": prompt_name},
            ) from exc

    async def generate_async(
        self,
        prompt_name: str,
        prompt_version: str,
        variables: dict[str, Any],
        *,
        model: str | None = None,
    ) -> LLMResponse:
        """Native async via google-genai's async client — no thread pool needed."""
        client = self._get_client()
        prompt_text, model_name = self._prepare(
            prompt_name, prompt_version, variables, model
        )
        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt_text,
            )
            return self._build_response(response, model_name)
        except ServiceUnavailableError:
            raise
        except Exception as exc:
            _logger.error("gemini_call_failed", error=str(exc), model=model_name)
            raise ServiceUnavailableError(
                message=f"Gemini call failed: {exc}",
                details={"model": model_name, "prompt": prompt_name},
            ) from exc
