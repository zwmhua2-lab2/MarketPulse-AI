"""Small immutable contracts for the PRE-01B-I2 Advisory ingress.

The production Host intentionally builds these objects only after a separately
authorised Gate-A activation.  Keeping the active configuration explicit makes
the ordinary, disabled runtime incapable of accidentally constructing a
provider, worker, queue, or database fence.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from .vocabulary import (
    ACTIVATION_DISABLED,
    ACTIVATION_GATE_A_SHADOW,
    ACTIVATION_GATE_B_PAPER,
    ADMISSION_GATE_A_DISABLED,
    ADVISORY_DEADLINE_POLICY_VERSION,
    ADVISORY_PROMPT_VERSION,
    ADVISORY_SCHEMA_VERSION,
    ADVISORY_TREATMENT_VERSION,
    BASELINE_POLICY_VERSION,
)


class AdvisoryConfigurationError(ValueError):
    """A startup epoch is incomplete or tries to enable an unsupported gate."""


@dataclass(frozen=True)
class AdvisoryActivationEpoch:
    """The immutable activation classification frozen once at Host composition."""

    activation_level: str
    epoch_id: str | None = None

    def __post_init__(self) -> None:
        if self.activation_level == ACTIVATION_GATE_B_PAPER:
            raise AdvisoryConfigurationError("GATE_B_PAPER is not implemented by PRE-01B-I2")
        if self.activation_level not in {ACTIVATION_DISABLED, ACTIVATION_GATE_A_SHADOW}:
            raise AdvisoryConfigurationError("unknown advisory activation level")
        if self.activation_level == ACTIVATION_GATE_A_SHADOW and not self.epoch_id:
            raise AdvisoryConfigurationError("Gate A requires a frozen advisory epoch id")

    @property
    def disabled_evidence_classification(self) -> str | None:
        """The only direct Edge classification licensed outside a SAVEPOINT."""

        return ADMISSION_GATE_A_DISABLED if self.activation_level == ACTIVATION_DISABLED else None


@dataclass(frozen=True)
class AdvisoryAdmissionConfig:
    """Complete deterministic Gate-A admission inputs; no provider handle exists here."""

    epoch: AdvisoryActivationEpoch
    config_version: str
    configured_provider_id: str
    configured_model_id: str
    deadline_duration_ms: int
    experiment_definition: dict[str, object]
    prompt_version: str = ADVISORY_PROMPT_VERSION
    schema_version: str = ADVISORY_SCHEMA_VERSION
    treatment_version: str = ADVISORY_TREATMENT_VERSION
    baseline_policy_version: str = BASELINE_POLICY_VERSION
    deadline_policy_version: str = ADVISORY_DEADLINE_POLICY_VERSION

    def __post_init__(self) -> None:
        if self.epoch.activation_level != ACTIVATION_GATE_A_SHADOW:
            raise AdvisoryConfigurationError("admission config is only valid for frozen Gate A")
        for field_name in (
            "config_version",
            "configured_provider_id",
            "configured_model_id",
            "prompt_version",
            "schema_version",
            "treatment_version",
            "baseline_policy_version",
            "deadline_policy_version",
        ):
            if not getattr(self, field_name):
                raise AdvisoryConfigurationError(f"{field_name} must be non-empty")
        if self.deadline_duration_ms <= 0:
            raise AdvisoryConfigurationError("deadline_duration_ms must be positive")
        if not self.experiment_definition:
            raise AdvisoryConfigurationError("experiment_definition must be non-empty")


@dataclass(frozen=True)
class CurrentAdvisoryAuthority:
    """One Host-frozen view of current advisory configuration, never an Invocation row."""

    activation_level: str
    config_version: str | None = None
    epoch_id: str | None = None
    experiment_definition_digest: str | None = None
    configured_provider_id: str | None = None
    configured_model_id: str | None = None
    prompt_version: str | None = None
    schema_version: str | None = None
    treatment_version: str | None = None
    baseline_policy_version: str | None = None
    deadline_policy_version: str | None = None

    @classmethod
    def disabled(cls) -> CurrentAdvisoryAuthority:
        return cls(activation_level=ACTIVATION_DISABLED)


@dataclass(frozen=True)
class RestartRecoveryCapability:
    """Host-issued startup-only authority, replacing caller-supplied booleans."""

    host_lifetime: str
    active: bool = True
    _issuer: object | None = None
    _owner_session_admission: Callable[[], Awaitable[bool]] | None = None

    def require_active(self) -> None:
        if not self.active or self._issuer is None:
            raise AdvisoryConfigurationError("restart recovery capability is revoked")

    async def admit_owner_session(self) -> bool:
        """Ask the issuing Host for the one final owner-session proof.

        A durable lifecycle owner calls this only after it holds the canonical
        rows and has completed all non-mutating predicates.  A missing or
        uncertain issuer proof is deliberately not interchangeable with a
        local capability boolean.
        """

        try:
            self.require_active()
            return bool(
                self._owner_session_admission is not None
                and await self._owner_session_admission()
            )
        except Exception:  # noqa: BLE001 - owner-proof uncertainty fails closed
            return False


@dataclass(frozen=True)
class LiveAttemptCapability:
    """Exact Host-owned live cancellation authority for one durable Attempt."""

    host_lifetime: str
    decision_invocation_id: str
    attempt_id: str
    cancellation_receipt: str
    active: bool = True
    _issuer: object | None = None
    _owner_session_admission: Callable[[], Awaitable[bool]] | None = None

    def matches(self, *, host_lifetime: str, decision_invocation_id: str, attempt_id: str) -> bool:
        return (
            self.active and bool(self.cancellation_receipt) and self.host_lifetime == host_lifetime
            and self._issuer is not None
            and self.decision_invocation_id == decision_invocation_id and self.attempt_id == attempt_id
        )

    async def admit_owner_session(self) -> bool:
        """Return true only after the issuer's FINAL owner-session proof."""

        try:
            return bool(
                self.active
                and self._issuer is not None
                and self._owner_session_admission is not None
                and await self._owner_session_admission()
            )
        except Exception:  # noqa: BLE001 - owner-proof uncertainty fails closed
            return False


class AdvisoryRetryPolicy(Protocol):
    """Typed retry assessment; never terminal authority."""

    def allows_retry(self, *, attempt_number: int) -> bool: ...


class HostAdvisoryAuthorityIssuer:
    """The narrow RuntimeHost issuer for non-durable lifecycle capabilities."""

    def __init__(
        self,
        host_lifetime: str,
        *,
        owner_session_admission: Callable[[], Awaitable[bool]] | None = None,
    ) -> None:
        self.host_lifetime = host_lifetime
        self._token = object()
        self._restart_open = True
        self._owner_session_admission = owner_session_admission

    def issue_restart_recovery(self) -> RestartRecoveryCapability:
        if not self._restart_open:
            raise AdvisoryConfigurationError("restart recovery authority is closed")
        return RestartRecoveryCapability(
            self.host_lifetime,
            _issuer=self._token,
            _owner_session_admission=self._owner_session_admission,
        )

    def revoke_restart_recovery(self) -> None:
        self._restart_open = False

    def issue_live_attempt(
        self, *, decision_invocation_id: str, attempt_id: str, cancellation_receipt: str
    ) -> LiveAttemptCapability:
        if not cancellation_receipt:
            raise AdvisoryConfigurationError("live cancellation receipt is required")
        return LiveAttemptCapability(
            self.host_lifetime, decision_invocation_id, attempt_id, cancellation_receipt,
            _issuer=self._token,
            _owner_session_admission=self._owner_session_admission,
        )


@dataclass(frozen=True)
class RecoveryInput:
    """Separated recovery dependencies, replacing opaque stale/retry booleans."""

    authority: CurrentAdvisoryAuthority
    capability: RestartRecoveryCapability
    retry_policy: AdvisoryRetryPolicy

    def require_valid(self) -> None:
        self.capability.require_active()


__all__ = [
    "AdvisoryActivationEpoch",
    "AdvisoryAdmissionConfig",
    "AdvisoryConfigurationError",
    "AdvisoryRetryPolicy",
    "CurrentAdvisoryAuthority",
    "HostAdvisoryAuthorityIssuer",
    "LiveAttemptCapability",
    "RecoveryInput",
    "RestartRecoveryCapability",
]
