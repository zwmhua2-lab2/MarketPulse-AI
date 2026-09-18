"""Small immutable contracts for the PRE-01B-I2 Advisory ingress.

The production Host intentionally builds these objects only after a separately
authorised Gate-A activation.  Keeping the active configuration explicit makes
the ordinary, disabled runtime incapable of accidentally constructing a
provider, worker, queue, or database fence.
"""

from __future__ import annotations

from dataclasses import dataclass

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


__all__ = [
    "AdvisoryActivationEpoch",
    "AdvisoryAdmissionConfig",
    "AdvisoryConfigurationError",
]
