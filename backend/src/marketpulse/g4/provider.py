from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Protocol

import httpx

from marketpulse.g3.models import DecisionSnapshot
from marketpulse.g3.service import redact

from .models import PositionReevaluation

REVIEW_PROMPT_VERSION = "g4-position-review-v1"
REVIEW_SCHEMA_VERSION = "g4-position-review-v1"


class PositionReviewPromptBuilder:
    version = REVIEW_PROMPT_VERSION

    def build(self, snapshot: DecisionSnapshot) -> str:
        payload = redact(snapshot.model_dump(mode="json"))
        return "\n\n".join(
            (
                (
                    "SYSTEM POLICY\nYou are reviewing ONE OPEN SPOT LONG position using only the "
                    "supplied frozen snapshot. Never call tools or execute trades. Return the "
                    "versioned structured review schema only. A missing or invalid answer changes "
                    "nothing: existing stop-loss and take-profit protection stays active."
                ),
                f"POSITION CONTEXT\n{json.dumps(payload['trading_context'], sort_keys=True)}",
                f"MARKET CONTEXT\n{json.dumps(payload['market_context'], sort_keys=True)}",
                f"MARKET EVOLUTION\n{json.dumps(payload['market_evolution'], sort_keys=True)}",
                f"STRATEGY CONTEXT\n{json.dumps(payload['strategies'], sort_keys=True)}",
                (
                    "REVIEW TASK\nChoose exactly one action from HOLD, ADD, REDUCE, CLOSE, "
                    "CANCEL_ADD, UPDATE_STOP, UPDATE_TP, UPDATE_INVALIDATION, REPLACE_PLAN and fill "
                    "only the fields that action requires."
                ),
            )
        )


class PositionReviewProvider(Protocol):
    """Provider boundary for position re-evaluation. Receives a frozen snapshot only."""

    async def review(self, snapshot: DecisionSnapshot, prompt: str) -> PositionReevaluation: ...


class DeterministicFakePositionReviewProvider:
    """Deterministic test provider. Not a real AI verification."""

    def __init__(
        self,
        response: PositionReevaluation
        | Callable[[DecisionSnapshot], PositionReevaluation | Awaitable[PositionReevaluation]],
    ) -> None:
        self._response = response
        self.calls = 0

    async def review(self, snapshot: DecisionSnapshot, prompt: str) -> PositionReevaluation:
        self.calls += 1
        result = self._response(snapshot) if callable(self._response) else self._response
        if hasattr(result, "__await__"):
            return await result  # type: ignore[no-any-return]
        return result  # type: ignore[return-value]


class OpenAIPositionReviewProvider:
    """Same single primary-provider boundary as G3; contract smoke is DEFERRED without a key."""

    def __init__(self, *, api_key: str, model: str, timeout_seconds: float, thinking: str) -> None:
        self.api_key, self.model, self.timeout_seconds, self.thinking = (
            api_key,
            model,
            timeout_seconds,
            thinking,
        )

    async def review(self, snapshot: DecisionSnapshot, prompt: str) -> PositionReevaluation:
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
        return PositionReevaluation.model_validate(json.loads(raw))
