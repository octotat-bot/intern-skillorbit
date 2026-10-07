"""LLM provider interface. Providers are swappable via ``LLM_PROVIDER``.

The rule-based analysis never calls this module; only the optional AI layer does.
"""

from __future__ import annotations

from typing import Protocol

from app import config


class LLMProvider(Protocol):
    """Anything that turns a prompt into a JSON string."""

    name: str
    model: str

    def generate_json(self, prompt: str) -> str:
        """Return the model's JSON response text."""
        ...


class GeminiProvider:
    """Google Gemini via the ``google-genai`` SDK."""

    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout_seconds: int) -> None:
        from google import genai  # optional dependency, imported only when used
        from google.genai import types

        self.model = model
        self._types = types
        self._client = genai.Client(api_key=api_key,
                                    http_options=types.HttpOptions(timeout=timeout_seconds * 1000))

    def generate_json(self, prompt: str) -> str:
        """Single low-temperature call constrained to JSON output."""
        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self._types.GenerateContentConfig(
                temperature=config.AI_TEMPERATURE, response_mime_type="application/json"
            ),
        )
        if not response.text:
            raise ValueError("Empty response from Gemini")
        return response.text


class ProviderUnavailable(RuntimeError):
    """No LLM provider is configured (disabled or missing key)."""


def get_provider() -> LLMProvider:
    """Build the configured provider.

    Raises:
        ProviderUnavailable: If disabled or the API key is missing.
    """
    name = config.LLM_PROVIDER.lower()
    if name == "none":
        raise ProviderUnavailable("AI mode is disabled (LLM_PROVIDER=none)")
    if name != "gemini":
        raise ProviderUnavailable(f"Unknown LLM_PROVIDER '{config.LLM_PROVIDER}'")
    if not config.GEMINI_API_KEY:
        raise ProviderUnavailable("No GEMINI_API_KEY configured")
    return GeminiProvider(config.GEMINI_API_KEY, config.GEMINI_MODEL, config.AI_TIMEOUT_SECONDS)
