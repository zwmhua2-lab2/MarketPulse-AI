"""PRE-01B-I2: deterministic Advisory identity, binding and package isolation.

Covers the D2 acceptance criteria that are decidable without a database:

* §12.1 identity derivations are pure functions of the exact frozen inputs;
* §0.3 decision 6 / §9.1 — ``feature_snapshot_hash`` really participates in the binding,
  so the accepted correction over the old draft is enforced rather than documented;
* §17.1 — timestamps entering a hash use the frozen RFC 3339 ``Z`` + 6-digit form and are
  UTC-normalized, so no DB session timezone or locale can change an identifier;
* §9.1 / §10.1 — an Evidence revision change yields a *different* binding, which is what
  makes "a new revision is a new invocation, never a rebinding" checkable;
* §23.2 / AC-23 — the advisory package imports no SE-02D aggregation projection and no
  economic mutation module, proved by reading the source rather than by trusting it.
"""

from __future__ import annotations

import ast
import asyncio
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from marketpulse.advisory.contracts import (
    AdvisoryActivationEpoch,
    AdvisoryAdmissionConfig,
    AdvisoryConfigurationError,
)
from marketpulse.advisory.fence import AdvisoryCheckoutKey, AdvisoryDbFence
from marketpulse.advisory.identity import (
    AdvisoryIdentityError,
    advisory_snapshot_id,
    attempt_id,
    baseline_arm_id,
    canonical_utc_timestamp,
    decision_invocation_id,
    experiment_definition_digest,
    experiment_id,
    final_decision_id,
    input_binding_digest,
    pair_id,
    snapshot_payload_hash,
    treatment_arm_id,
)
from marketpulse.advisory.ingress import AdvisoryIngress
from marketpulse.advisory.vocabulary import (
    ACTIVATION_DISABLED,
    ADMISSION_STATES,
    ADMISSION_UNSTAGED,
    ADVISORY_BINDING_VERSION,
    ADVISORY_SNAPSHOT_CONTRACT_VERSION,
    ATTEMPT_STATES,
    BASELINE_ARM_LABEL,
    FROZEN_VERSION_LITERALS,
    I2_IMPLEMENTED_ACTIVATION_LEVELS,
    INVOCATION_STATES,
    NO_ATTEMPT_FINAL_PAIRS,
    PARTICIPATION_NO_LONG_UNBOUND,
    REASON_ADMISSION_STAGING_FAILED_UNBOUND,
    TREATMENT_ARM_LABEL,
)
from marketpulse.edge.hashing import canonical_digest
from marketpulse.g2.models import AdvisoryWorkRef

START = datetime(2026, 9, 17, 2, 14, 42, 123456, tzinfo=UTC)
DEADLINE = START + timedelta(seconds=30)
ADVISORY_PACKAGE = Path(__file__).resolve().parents[1] / "src" / "marketpulse" / "advisory"

#: Modules the Gate A advisory path must never reach. `aggregation_snapshot` is the
#: SE-02D-I02 projection (D2 §23.2); the rest are the economic mutation authorities D2 §11
#: forbids a shadow consumer from holding.
FORBIDDEN_ADVISORY_IMPORTS = (
    "marketpulse.edge.aggregation_snapshot",
    "marketpulse.edge.aggregation_orchestration",
    "marketpulse.g2.runtime",
    "marketpulse.g3.service",
    "marketpulse.g4.planning",
    "marketpulse.g4.risk_gate",
    "marketpulse.g4.protection",
    "marketpulse.g4.reconciliation",
    "marketpulse.g4.recovery",
    "marketpulse.g4.orchestrator",
    "marketpulse.runtime_host",
)


def _binding(**overrides: object) -> str:
    values: dict[str, object] = {
        "opportunity_id": "op-1",
        "evidence_id": "ev-1",
        "evidence_revision": 1,
        "evidence_hash": "a" * 64,
        "feature_snapshot_hash": "b" * 64,
        "snapshot_id": "snap-1",
        "snapshot_payload_hash": "c" * 64,
        "state_version": 7,
        "config_version": "cfg-1",
        "family_id": "BREAKOUT_RETEST",
        "family_version": "f1",
        "instrument_id": "BTC-USDT",
        "market_type": "SPOT",
        "advisory_config_epoch_id": "epoch-1",
        "decision_requested_at": START,
        "deadline_duration_ms": 30_000,
        "deadline_policy_version": "pre01a-absolute-deadline-v1",
        "decision_deadline_at": DEADLINE,
    }
    values.update(overrides)
    return input_binding_digest(**values)  # type: ignore[arg-type]


def test_disabled_epoch_is_the_only_direct_edge_classification_and_gate_b_fails_closed():
    disabled = AdvisoryActivationEpoch(ACTIVATION_DISABLED)

    assert disabled.disabled_evidence_classification == "GATE_A_DISABLED"
    with pytest.raises(AdvisoryConfigurationError, match="GATE_B_PAPER"):
        AdvisoryActivationEpoch("GATE_B_PAPER")
    with pytest.raises(AdvisoryConfigurationError, match="epoch id"):
        AdvisoryActivationEpoch("GATE_A_SHADOW")
    with pytest.raises(AdvisoryConfigurationError, match="only valid for frozen Gate A"):
        AdvisoryAdmissionConfig(
            epoch=disabled,
            config_version="cfg",
            configured_provider_id="fake",
            configured_model_id="fake",
            deadline_duration_ms=1,
            experiment_definition={"fixture": "only"},
        )


def test_db_fence_is_immediate_bounded_and_never_consumes_protection_reserve():
    fence = AdvisoryDbFence(effective_db_capacity=3, protection_reserve=1)
    first = fence.try_acquire()
    second = fence.try_acquire()

    assert first is not None
    assert second is not None
    assert fence.try_acquire() is None
    assert fence.held == 2
    assert fence.snapshot() == {
        "capacity": 2,
        "held": 2,
        "available": 0,
        "uncertain": 0,
        "closed": False,
    }


def test_post_commit_offer_is_queue_only_when_full_and_never_acquires_a_db_lease():
    async def scenario() -> None:
        # No session factory is deliberately configured: any DB/session path would
        # fail this test.  A full offer reports only the immediate queue result.
        fence = AdvisoryDbFence(effective_db_capacity=3, protection_reserve=1)
        ingress = AdvisoryIngress(fence, queue_capacity=1)
        first = AdvisoryWorkRef("invocation-1", DEADLINE)
        rejected = AdvisoryWorkRef("invocation-2", DEADLINE)

        assert await ingress.post_commit_offer(first)
        before = fence.snapshot()
        assert not await ingress.post_commit_offer(rejected)
        assert ingress.take_nowait() == first
        assert fence.snapshot() == before

    asyncio.run(scenario())


def _lease_key(fence: AdvisoryDbFence, generation: int = 1) -> AdvisoryCheckoutKey:
    return AdvisoryCheckoutKey(fence.runtime_epoch, "entry-1", generation)


def test_db_fence_releases_only_after_exact_pool_return_and_owner_completion():
    fence = AdvisoryDbFence(effective_db_capacity=3, protection_reserve=1, runtime_epoch="epoch")
    lease = fence.try_acquire()
    assert lease is not None
    key = _lease_key(fence)
    lease.bind(key, "cleanup-1")

    fence.observe_pool_return(key, "cleanup-1")
    assert fence.held == 1
    fence.owner_completed(lease, "cleanup-1")
    assert fence.snapshot()["available"] == 2


def test_db_fence_owner_only_duplicate_and_old_generation_never_release():
    fence = AdvisoryDbFence(effective_db_capacity=3, protection_reserve=1, runtime_epoch="epoch")
    lease = fence.try_acquire()
    assert lease is not None
    key = _lease_key(fence, 2)
    lease.bind(key, "cleanup-2")

    fence.owner_completed(lease, "cleanup-2")
    fence.owner_completed(lease, "cleanup-2")
    fence.observe_pool_return(_lease_key(fence, 1), "cleanup-2")
    assert fence.held == 1
    fence.observe_pool_return(key, "late-cleanup")
    assert fence.held == 1
    fence.observe_pool_return(key, "cleanup-2")
    assert fence.held == 0


def test_db_fence_uncertain_holder_remains_counted_and_shutdown_closes_new_work():
    fence = AdvisoryDbFence(effective_db_capacity=3, protection_reserve=1, runtime_epoch="epoch")
    lease = fence.try_acquire()
    assert lease is not None
    lease.bind(_lease_key(fence), "cleanup-3")
    lease.retire_uncertain()
    fence.close_new_acquisition()

    assert fence.snapshot()["uncertain"] == 1
    assert fence.try_acquire() is None


def test_db_fence_hard_invalidation_requires_invalidate_checkin_none_and_owner_success():
    fence = AdvisoryDbFence(effective_db_capacity=3, protection_reserve=1, runtime_epoch="epoch")
    lease = fence.try_acquire()
    assert lease is not None
    key = _lease_key(fence)
    lease.bind(key, "cleanup-4")

    fence.observe_hard_invalidation(key, "cleanup-4")
    fence.owner_completed(lease, "cleanup-4")
    assert fence.held == 1
    fence.observe_pool_return(key, "cleanup-4", checkin_none=True)
    assert fence.held == 0


# ---------------------------------------------------------------------------- timestamp form


def test_canonical_timestamp_is_rfc3339_z_with_six_digits() -> None:
    assert canonical_utc_timestamp(START) == "2026-09-17T02:14:42.123456Z"


def test_canonical_timestamp_pads_fractional_seconds() -> None:
    value = datetime(2026, 9, 17, 2, 14, 42, tzinfo=UTC)
    assert canonical_utc_timestamp(value) == "2026-09-17T02:14:42.000000Z"


def test_canonical_timestamp_normalizes_non_utc_offsets() -> None:
    offset = timezone(timedelta(hours=8))
    shifted = START.astimezone(offset)
    assert canonical_utc_timestamp(shifted) == canonical_utc_timestamp(START)


def test_canonical_timestamp_rejects_naive_datetime() -> None:
    with pytest.raises(AdvisoryIdentityError):
        canonical_utc_timestamp(datetime(2026, 9, 17, 2, 14, 42))  # noqa: DTZ001


def test_binding_is_timezone_insensitive() -> None:
    """A binding built from the same instant in another offset is the same binding."""

    offset = timezone(timedelta(hours=-5))
    assert _binding(decision_deadline_at=DEADLINE.astimezone(offset)) == _binding()


# ---------------------------------------------------------------------------- determinism


def test_snapshot_payload_hash_is_deterministic_for_same_payload() -> None:
    payload = {"instrument_id": "BTC-USDT", "state_version": 7, "nested": {"a": [1, 2]}}
    assert snapshot_payload_hash(payload) == snapshot_payload_hash(dict(payload))


def test_snapshot_payload_hash_changes_with_payload() -> None:
    assert snapshot_payload_hash({"a": 1}) != snapshot_payload_hash({"a": 2})


def test_snapshot_id_is_deterministic_and_payload_sensitive() -> None:
    first = advisory_snapshot_id(opportunity_id="op-1", evidence_id="ev-1", payload_hash="h1")
    assert first == advisory_snapshot_id(opportunity_id="op-1", evidence_id="ev-1", payload_hash="h1")
    assert first != advisory_snapshot_id(opportunity_id="op-1", evidence_id="ev-1", payload_hash="h2")
    assert first != advisory_snapshot_id(opportunity_id="op-1", evidence_id="ev-2", payload_hash="h1")
    assert first != advisory_snapshot_id(opportunity_id="op-2", evidence_id="ev-1", payload_hash="h1")


def test_binding_is_deterministic() -> None:
    assert _binding() == _binding()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("opportunity_id", "op-2"),
        ("evidence_id", "ev-2"),
        ("evidence_revision", 2),
        ("evidence_hash", "d" * 64),
        # D2 §0.3 decision 6 / §9.1: the old draft omitted this field from the digest.
        ("feature_snapshot_hash", "e" * 64),
        ("snapshot_id", "snap-2"),
        ("snapshot_payload_hash", "f" * 64),
        ("state_version", 8),
        ("config_version", "cfg-2"),
        ("family_id", "OTHER"),
        ("family_version", "f2"),
        ("instrument_id", "ETH-USDT"),
        ("market_type", "SWAP"),
        ("advisory_config_epoch_id", "epoch-2"),
        ("decision_requested_at", START + timedelta(seconds=1)),
        ("deadline_duration_ms", 60_000),
        ("deadline_policy_version", "other-deadline-policy"),
        ("decision_deadline_at", DEADLINE + timedelta(seconds=1)),
    ],
)
def test_every_binding_field_participates(field: str, value: object) -> None:
    assert _binding(**{field: value}) != _binding(), f"{field} is missing from the binding"


def test_new_evidence_revision_is_a_new_binding_not_a_rebinding() -> None:
    """D2 §10.1: a superseding revision may not reuse the predecessor's invocation."""

    revision_one = _binding(evidence_revision=1, evidence_id="ev-1")
    revision_two = _binding(evidence_revision=2, evidence_id="ev-2")
    assert revision_one != revision_two


# ---------------------------------------------------------------------------- derivations


def _definition() -> dict[str, object]:
    return {
        "placement": "C_TRADE_DECISION",
        "baseline_policy_version": "ALL_ELIGIBLE_LONG_SHADOW_V1",
        "treatment_version": "pre01a-real-ai-treatment-v1",
        "configured_provider_id": "fake-provider",
        "configured_model_id": "fake-model",
    }


def test_experiment_identity_is_definition_addressed() -> None:
    assert experiment_id(_definition()) == experiment_id(dict(_definition()))
    assert experiment_definition_digest(_definition()) == experiment_definition_digest(
        dict(_definition())
    )
    changed = dict(_definition())
    changed["configured_model_id"] = "other-model"
    assert experiment_id(changed) != experiment_id(_definition())
    assert experiment_definition_digest(changed) != experiment_definition_digest(_definition())


def test_experiment_identity_rejects_empty_definition() -> None:
    with pytest.raises(AdvisoryIdentityError):
        experiment_id({})
    with pytest.raises(AdvisoryIdentityError):
        experiment_definition_digest({})


def test_pair_and_arm_identity_follow_the_binding() -> None:
    experiment = experiment_id(_definition())
    pair = pair_id(experiment_id=experiment, input_binding_digest=_binding())
    assert pair == pair_id(experiment_id=experiment, input_binding_digest=_binding())
    assert pair != pair_id(experiment_id=experiment, input_binding_digest=_binding(evidence_id="ev-9"))

    baseline = baseline_arm_id(pair_id=pair)
    treatment = treatment_arm_id(pair_id=pair)
    assert baseline != treatment
    # Build the canonical preimages independently: these expected values must never
    # delegate back to either arm helper under test.
    assert baseline == canonical_digest("pre01a-arm-v1", pair, "WITHOUT_AI_BASELINE")
    assert treatment == canonical_digest("pre01a-arm-v1", pair, "REAL_AI_TREATMENT")
    # The arm labels are the frozen contract labels, not free-form strings.
    assert baseline == baseline_arm_id(pair_id=pair)
    assert BASELINE_ARM_LABEL == "WITHOUT_AI_BASELINE"
    assert TREATMENT_ARM_LABEL == "REAL_AI_TREATMENT"


def test_invocation_identity_is_deterministic_and_fully_bound() -> None:
    kwargs: dict[str, object] = {
        "experiment_id": "exp-1",
        "pair_id": "pair-1",
        "treatment_arm_id": "arm-t",
        "input_binding_digest": "bind-1",
        "prompt_version": "p1",
        "schema_version": "s1",
        "treatment_version": "t1",
        "configured_provider_id": "fake-provider",
        "configured_model_id": "fake-model",
    }
    first = decision_invocation_id(**kwargs)  # type: ignore[arg-type]
    assert first == decision_invocation_id(**kwargs)  # type: ignore[arg-type]
    for field in kwargs:
        changed = dict(kwargs)
        changed[field] = "changed"
        assert decision_invocation_id(**changed) != first, field  # type: ignore[arg-type]


def test_attempt_identity_is_per_attempt_and_invocation_scoped() -> None:
    invocation = "inv-1"
    assert attempt_id(decision_invocation_id=invocation, attempt_number=1) == attempt_id(
        decision_invocation_id=invocation, attempt_number=1
    )
    assert attempt_id(decision_invocation_id=invocation, attempt_number=1) != attempt_id(
        decision_invocation_id=invocation, attempt_number=2
    )
    assert attempt_id(decision_invocation_id=invocation, attempt_number=1) != attempt_id(
        decision_invocation_id="inv-2", attempt_number=1
    )
    with pytest.raises(AdvisoryIdentityError):
        attempt_id(decision_invocation_id=invocation, attempt_number=0)


def test_final_decision_identity_depends_only_on_the_invocation() -> None:
    assert final_decision_id(decision_invocation_id="inv-1") == final_decision_id(
        decision_invocation_id="inv-1"
    )
    assert final_decision_id(decision_invocation_id="inv-1") != final_decision_id(
        decision_invocation_id="inv-2"
    )


def test_domains_are_separated() -> None:
    """Identical payloads under different domains must never collide."""

    experiment = "exp-1"
    binding = "bind-1"
    assert pair_id(experiment_id=experiment, input_binding_digest=binding) != baseline_arm_id(
        pair_id=pair_id(experiment_id=experiment, input_binding_digest=binding)
    )
    assert decision_invocation_id(
        experiment_id=experiment,
        pair_id=binding,
        treatment_arm_id="arm",
        input_binding_digest=binding,
        prompt_version="p",
        schema_version="s",
        treatment_version="t",
        configured_provider_id="fake-provider",
        configured_model_id="fake-model",
    ) != final_decision_id(decision_invocation_id=binding)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("opportunity_id", ""),
        ("evidence_hash", ""),
        ("evidence_revision", 0),
        ("evidence_revision", -1),
        ("state_version", -1),
        ("deadline_duration_ms", 0),
    ],
)
def test_binding_refuses_incomplete_identity_facts(field: str, value: object) -> None:
    with pytest.raises(AdvisoryIdentityError):
        _binding(**{field: value})


def test_binding_accepts_the_legal_zero_state_version() -> None:
    """A symbol with no durable G2 row yet is at version 0, which is a legal binding."""

    assert _binding(state_version=0) == _binding(state_version=0)
    assert _binding(state_version=0) != _binding()


def test_binding_frozen_version_is_the_declared_literal() -> None:
    assert ADVISORY_BINDING_VERSION == "pre01b-advisory-input-binding-v1"
    assert ADVISORY_SNAPSHOT_CONTRACT_VERSION == "pre01b-advisory-snapshot-payload-v1"


# ---------------------------------------------------------------------------- vocabulary


def test_frozen_version_literal_set_is_complete_and_explicit() -> None:
    """D2 §12.2: every hash version literal is frozen in one auditable place."""

    required = {
        "snapshot_contract_version",
        "binding_version",
        "experiment_definition_version",
        "seed_version",
        "deadline_policy_version",
        "config_epoch_version",
        "prompt_version",
        "schema_version",
        "treatment_version",
        "baseline_policy_version",
    }
    assert set(FROZEN_VERSION_LITERALS) == required
    assert all(value for value in FROZEN_VERSION_LITERALS.values())


def test_vocabulary_matches_the_frozen_contract_tokens() -> None:
    assert ADMISSION_UNSTAGED == "UNSTAGED"
    assert REASON_ADMISSION_STAGING_FAILED_UNBOUND == "ADMISSION_STAGING_FAILED_UNBOUND"
    assert PARTICIPATION_NO_LONG_UNBOUND == "NO_LONG_UNBOUND"
    assert ADMISSION_STATES == (
        "LEGACY_PRE_I2",
        "UNSTAGED",
        "GATE_A_DISABLED",
        "INVOCATION_CREATED",
        "ADMISSION_FAILED_FINAL",
    )
    assert INVOCATION_STATES == ("ADMITTED", "ACTIVE", "RETRY_PENDING", "FINAL")
    assert NO_ATTEMPT_FINAL_PAIRS == (
        ("STALE_DECISION", "DEADLINE_EXPIRED_BEFORE_PROVIDER"),
        ("CAPACITY_BLOCKED", "ADVISORY_QUEUE_REJECTED"),
        ("CAPACITY_BLOCKED", "ADVISORY_DB_CAPACITY_UNAVAILABLE"),
        ("STALE_DECISION", "EVIDENCE_SUPERSEDED_BEFORE_PROVIDER"),
        ("STALE_DECISION", "OPPORTUNITY_STALE_BEFORE_PROVIDER"),
        ("STALE_DECISION", "ACTIVATION_DISABLED_BEFORE_PROVIDER"),
        ("STALE_DECISION", "BINDING_INVALID_BEFORE_PROVIDER"),
        ("STALE_DECISION", "EXPERIMENT_CONFIG_MISMATCH_BEFORE_PROVIDER"),
        ("INVALID_SCHEMA", "SHUTDOWN_BEFORE_PROVIDER"),
    )
    # D2 §22: I2 may only wire DISABLED and GATE_A_SHADOW; GATE_B_PAPER stays fail-closed.
    assert I2_IMPLEMENTED_ACTIVATION_LEVELS == (ACTIVATION_DISABLED, "GATE_A_SHADOW")
    assert "GATE_B_PAPER" not in I2_IMPLEMENTED_ACTIVATION_LEVELS
    assert ATTEMPT_STATES == (
        "STARTED",
        "COMPLETED",
        "PROCESS_LOST",
        "ABANDONED",
        "DUPLICATE_SUPPRESSED",
        "LATE_RESULT",
    )


# ---------------------------------------------------------------------------- isolation


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def test_advisory_package_imports_no_forbidden_authority() -> None:
    """AC-23 / D2 §23.2: SE-02D import count = 0 and no economic mutation authority."""

    sources = sorted(ADVISORY_PACKAGE.glob("*.py"))
    assert sources, "the advisory package must contain source modules"
    for path in sources:
        imported = _imported_modules(path)
        for forbidden in FORBIDDEN_ADVISORY_IMPORTS:
            offenders = {
                name for name in imported if name == forbidden or name.startswith(f"{forbidden}.")
            }
            assert not offenders, f"{path.name} imports {forbidden}"


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """Ids of every docstring constant node, so documentation is not scanned as code."""

    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                value = body[0].value
                if isinstance(value.value, str):
                    docstrings.add(id(value))
    return docstrings


def _code_tokens(path: Path) -> set[str]:
    """Every identifier and non-docstring string constant in one module's code."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    docstrings = _docstring_nodes(tree)
    tokens: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            tokens.add(node.id)
        elif isinstance(node, ast.Attribute):
            tokens.add(node.attr)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            for alias in node.names:
                tokens.add(alias.name)
                if alias.asname:
                    tokens.add(alias.asname)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            tokens.add(node.value)
    return tokens


def test_advisory_sources_contain_no_forbidden_authority_reference() -> None:
    """A code-level guard on top of the import guard.

    Docstrings are excluded: `__init__.py` documents what the package may *not* reach, and
    naming a forbidden authority in prose is not the same as holding a handle to it. What
    this asserts is that no expression, identifier or literal in the executable code names
    one of those authorities.
    """

    forbidden_tokens = (
        "persist_trade_plan",
        "TradePlanManager",
        "G3Workflow",
        "SystemRiskGate",
        "PaperExecutionService",
        "aggregation_snapshot",
    )
    for path in sorted(ADVISORY_PACKAGE.glob("*.py")):
        tokens = _code_tokens(path)
        for token in forbidden_tokens:
            assert token not in tokens, f"{path.name} references {token} in code"
