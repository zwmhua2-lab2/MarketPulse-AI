from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Protocol

import httpx

from .models import AIAnalysis, DecisionSnapshot


class AIProvider(Protocol):
    """Provider boundary: receives a frozen snapshot only, never repositories or execution services."""

    async def analyze(self, snapshot: DecisionSnapshot, prompt: str) -> AIAnalysis: ...


class DeterministicFakeAIProvider:
    """Test-only provider; production wiring remains provider-neutral."""

    def __init__(
        self,
        response: AIAnalysis | Callable[[DecisionSnapshot], AIAnalysis | Awaitable[AIAnalysis]],
    ) -> None:
        self._response = response
        self.calls = 0

    async def analyze(self, snapshot: DecisionSnapshot, prompt: str) -> AIAnalysis:
        self.calls += 1
        result = self._response(snapshot) if callable(self._response) else self._response
        if hasattr(result, "__await__"):
            return await result  # type: ignore[no-any-return]
        return result  # type: ignore[return-value]


class OpenAIResponsesProvider:
    """Single V1 primary-model adapter. It receives only rendered frozen-snapshot prompts."""

    def __init__(self, *, api_key: str, model: str, timeout_seconds: float, thinking: str) -> None:
        self.api_key, self.model, self.timeout_seconds, self.thinking = (
            api_key,
            model,
            timeout_seconds,
            thinking,
        )

    async def analyze(self, snapshot: DecisionSnapshot, prompt: str) -> AIAnalysis:
        body = {
            "model": self.model,
            "input": prompt,
            "reasoning": {"effort": self.thinking},
            "text": {"format": {"type": "json_object"}},
        }
        async with httpx.AsyncClient(
            base_url="https://api.openai.com", timeout=self.timeout_seconds
        ) as client:
            response = await client.post(
                "/v1/responses", headers={"Authorization": f"Bearer {self.api_key}"}, json=body
            )
            response.raise_for_status()
        payload = response.json()
        raw = payload.get("output_text")
        if not isinstance(raw, str):
            raise TypeError("provider_missing_output_text")
        return AIAnalysis.model_validate(json.loads(raw))
