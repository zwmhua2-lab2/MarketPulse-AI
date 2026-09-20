"""Small immutable contracts for the PRE-01B-I2 Advisory ingress.

The production Host intentionally builds these objects only after a separately
authorised Gate-A activation.  Keeping the active configuration explicit makes
the ordinary, disabled runtime incapable of accidentally constructing a
provider, worker, queue, or database fence.
"""

from __future__ import annotations

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
class _LiveAttemptIssuance:
    """Issuer-owned exact facts for one non-durable live credential."""

    host_lifetime: str
    decision_invocation_id: str
    attempt_id: str
    cancellation_receipt: str


class RestartRecoveryCapability:
    """One non-forgeable startup-only capability issued by the RuntimeHost root."""

    __slots__ = ("_credential", "_issuer", "host_lifetime")

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise AdvisoryConfigurationError("RestartRecoveryCapability is RuntimeHost-issued only")

    @classmethod
    def _issue(cls, issuer: HostAdvisoryAuthorityIssuer, credential: object) -> RestartRecoveryCapability:
        capability = object.__new__(cls)
        capability.host_lifetime = issuer.host_lifetime
        capability._issuer = issuer
        capability._credential = credential
        return capability

    def require_active(self) -> None:
        if not self._issuer._restart_is_active(self):
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
            return await self._issuer._admit_restart(self)
        except Exception:  # noqa: BLE001 - owner-proof uncertainty fails closed
            return False


class LiveAttemptCapability:
    """Exact Host-owned live cancellation authority for one durable Attempt."""

    __slots__ = ("_credential", "_issued", "_issuer")

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise AdvisoryConfigurationError("LiveAttemptCapability is RuntimeHost-issued only")

    @classmethod
    def _issue(
        cls,
        issuer: HostAdvisoryAuthorityIssuer,
        credential: object,
    ) -> LiveAttemptCapability:
        capability = object.__new__(cls)
        object.__setattr__(capability, "_issuer", issuer)
        object.__setattr__(capability, "_credential", credential)
        object.__setattr__(capability, "_issued", True)
        return capability

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_issued", False):
            raise AttributeError("LiveAttemptCapability identity is issuer-issued and immutable")
        object.__setattr__(self, name, value)

    def matches(self, *, host_lifetime: str, decision_invocation_id: str, attempt_id: str) -> bool:
        return self._issuer._live_matches(
            self,
            host_lifetime=host_lifetime,
            decision_invocation_id=decision_invocation_id,
            attempt_id=attempt_id,
        )

    async def admit_owner_session(self) -> bool:
        """Return true only after the issuer's FINAL owner-session proof."""

        try:
            return await self._issuer._admit_live(self)
        except Exception:  # noqa: BLE001 - owner-proof uncertainty fails closed
            return False


class AdvisoryRetryPolicy(Protocol):
    """Typed retry assessment; never terminal authority."""

    def allows_retry(self, *, attempt_number: int) -> bool: ...


class HostAdvisoryAuthorityIssuer:
    """The one RuntimeHost-bound issuer for non-durable lifecycle capabilities."""

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise AdvisoryConfigurationError("HostAdvisoryAuthorityIssuer is RuntimeHost-bound only")

    @classmethod
    def _for_host_root(cls, host: object) -> HostAdvisoryAuthorityIssuer:
        """Bind issuance and final proof to the actual RuntimeHost ownership root."""

        issuer = object.__new__(cls)
        host_lifetime = getattr(host, "instance_id", None)
        if not isinstance(host_lifetime, str) or not host_lifetime:
            raise AdvisoryConfigurationError("RuntimeHost lifetime is unavailable")
        issuer.host_lifetime = host_lifetime
        issuer._host = host
        issuer._restart_open = True
        issuer._live_open = True
        issuer._restart_credential = object()
        issuer._live_issuances: dict[object, _LiveAttemptIssuance] = {}
        return issuer

    def _is_current_host_root(self) -> bool:
        return getattr(self._host, "_advisory_authority_issuer", None) is self

    def _restart_is_active(self, capability: RestartRecoveryCapability) -> bool:
        return (
            self._restart_open
            and self._is_current_host_root()
            and capability._issuer is self
            and capability._credential is self._restart_credential
        )

    def _live_issuance_for(self, capability: LiveAttemptCapability) -> _LiveAttemptIssuance | None:
        if capability._issuer is not self:
            return None
        return self._live_issuances.get(capability._credential)

    def _live_is_active(self, capability: LiveAttemptCapability) -> bool:
        return (
            self._live_open
            and self._is_current_host_root()
            and self._live_issuance_for(capability) is not None
        )

    def _live_matches(
        self,
        capability: LiveAttemptCapability,
        *,
        host_lifetime: str,
        decision_invocation_id: str,
        attempt_id: str,
    ) -> bool:
        issuance = self._live_issuance_for(capability)
        return (
            issuance is not None
            and self._live_is_active(capability)
            and bool(issuance.cancellation_receipt)
            and issuance.host_lifetime == self.host_lifetime == host_lifetime
            and issuance.decision_invocation_id == decision_invocation_id
            and issuance.attempt_id == attempt_id
        )

    async def _admit_restart(self, capability: RestartRecoveryCapability) -> bool:
        if not self._restart_is_active(capability):
            return False
        return await self._admit_host_owner_session()

    async def _admit_live(self, capability: LiveAttemptCapability) -> bool:
        if not self._live_is_active(capability):
            return False
        return await self._admit_host_owner_session()

    async def _admit_host_owner_session(self) -> bool:
        try:
            return bool(await self._host.admit_singleton_owner_session())
        except Exception:  # noqa: BLE001 - owner-proof uncertainty fails closed
            return False

    def issue_restart_recovery(self) -> RestartRecoveryCapability:
        if not self._restart_open:
            raise AdvisoryConfigurationError("restart recovery authority is closed")
        if not self._is_current_host_root():
            raise AdvisoryConfigurationError("RuntimeHost authority root is unavailable")
        return RestartRecoveryCapability._issue(self, self._restart_credential)

    def revoke_restart_recovery(self) -> None:
        self._restart_open = False

    def revoke_all(self) -> None:
        """Invalidate every process-local capability when this Host loses authority."""

        self._restart_open = False
        self._live_open = False
        self._live_issuances.clear()

    def issue_live_attempt(
        self, *, decision_invocation_id: str, attempt_id: str, cancellation_receipt: str
    ) -> LiveAttemptCapability:
        if not cancellation_receipt:
            raise AdvisoryConfigurationError("live cancellation receipt is required")
        if not decision_invocation_id or not attempt_id:
            raise AdvisoryConfigurationError("live capability requires exact invocation and attempt")
        if not self._live_open or not self._is_current_host_root():
            raise AdvisoryConfigurationError("RuntimeHost authority root is unavailable")
        credential = object()
        self._live_issuances[credential] = _LiveAttemptIssuance(
            host_lifetime=self.host_lifetime,
            decision_invocation_id=decision_invocation_id,
            attempt_id=attempt_id,
            cancellation_receipt=cancellation_receipt,
        )
        return LiveAttemptCapability._issue(
            self,
            credential,
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
