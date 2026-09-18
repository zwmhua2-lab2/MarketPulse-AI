"""Frozen literals for the PRE-01B-I2 AdvisoryIngress contract.

Every token here is either quoted verbatim from the accepted PRE-01B-D2 contract or is a
**version literal frozen by this implementation** as D2 §12.2 explicitly requires:

    "每个 hash 的 version literal 属 I2 实现契约，须在实现窗口逐字冻结（教训：
     SE-02D-D01 `uncertainty_method_version` 曾缺失 literal ⇒ Human Design
     Clarification 补齐；D2 把该项列入 I2 实现前置核对清单）"

So this module is the single place where an auditor can check the frozen version set, and
nothing in the package may inline a domain tag or a vocabulary token instead. Changing a
token here changes every derived identifier, which is exactly the intended blast radius.

Tokens that D2 fixes verbatim are marked "D2 literal" with the section that fixes them.
The remaining `-v1` version strings are the implementation-frozen pre-contract versions
called for by §12.2, and are collected in ``FROZEN_VERSION_LITERALS`` so a reviewer can
see the complete set in one read.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------------------
# Activation (D2 §22)
# ---------------------------------------------------------------------------------------
ACTIVATION_DISABLED = "DISABLED"  # D2 literal
ACTIVATION_GATE_A_SHADOW = "GATE_A_SHADOW"  # D2 literal
ACTIVATION_GATE_B_PAPER = "GATE_B_PAPER"  # D2 literal

ACTIVATION_LEVELS = (ACTIVATION_DISABLED, ACTIVATION_GATE_A_SHADOW, ACTIVATION_GATE_B_PAPER)
#: D2 §22: I2 may only wire DISABLED and GATE_A_SHADOW. GATE_B_PAPER must fail closed.
I2_IMPLEMENTED_ACTIVATION_LEVELS = (ACTIVATION_DISABLED, ACTIVATION_GATE_A_SHADOW)

# ---------------------------------------------------------------------------------------
# Evidence durable admission accounting (D2 §8.3, §24.2)
# ---------------------------------------------------------------------------------------
ADMISSION_LEGACY_PRE_I2 = "LEGACY_PRE_I2"  # D2 literal
ADMISSION_UNSTAGED = "UNSTAGED"  # D2 literal; the new-row PostgreSQL default
ADMISSION_GATE_A_DISABLED = "GATE_A_DISABLED"  # D2 literal
ADMISSION_INVOCATION_CREATED = "INVOCATION_CREATED"  # D2 literal
ADMISSION_FAILED_FINAL = "ADMISSION_FAILED_FINAL"  # D2 literal

ADMISSION_STATES = (
    ADMISSION_LEGACY_PRE_I2,
    ADMISSION_UNSTAGED,
    ADMISSION_GATE_A_DISABLED,
    ADMISSION_INVOCATION_CREATED,
    ADMISSION_FAILED_FINAL,
)
#: The safe states that are bare markers: no seed, no experiment/pair/arm, no Invocation.
ADMISSION_BARE_STATES = (
    ADMISSION_LEGACY_PRE_I2,
    ADMISSION_UNSTAGED,
    ADMISSION_GATE_A_DISABLED,
)

REASON_ADMISSION_STAGING_FAILED_UNBOUND = "ADMISSION_STAGING_FAILED_UNBOUND"  # D2 literal

PARTICIPATION_PARTICIPATE_LONG = "PARTICIPATE_LONG"  # D2 literal (§13.2)
PARTICIPATION_NO_LONG = "NO_LONG"  # D2 literal (§13.2)
PARTICIPATION_NO_LONG_UNBOUND = "NO_LONG_UNBOUND"  # D2 literal (§8.3, §32.2)

# ---------------------------------------------------------------------------------------
# Invocation execution state (D2 §14.1) — durable execution state, not a DecisionStatus
# ---------------------------------------------------------------------------------------
INVOCATION_ADMITTED = "ADMITTED"  # D2 literal
INVOCATION_ACTIVE = "ACTIVE"  # D2 literal
INVOCATION_RETRY_PENDING = "RETRY_PENDING"  # D2 literal
INVOCATION_FINAL = "FINAL"  # D2 literal

INVOCATION_STATES = (
    INVOCATION_ADMITTED,
    INVOCATION_ACTIVE,
    INVOCATION_RETRY_PENDING,
    INVOCATION_FINAL,
)

# ---------------------------------------------------------------------------------------
# Attempt lifecycle (D2 §14.3, §14.4, §15, §20.2) — every token appears verbatim in D2
# ---------------------------------------------------------------------------------------
ATTEMPT_STARTED = "STARTED"  # D2 literal
ATTEMPT_COMPLETED = "COMPLETED"
ATTEMPT_PROCESS_LOST = "PROCESS_LOST"  # D2 literal
ATTEMPT_ABANDONED = "ABANDONED"  # D2 literal
ATTEMPT_DUPLICATE_SUPPRESSED = "DUPLICATE_SUPPRESSED"  # D2 literal
ATTEMPT_LATE_RESULT = "LATE_RESULT"  # D2 literal

ATTEMPT_STATES = (
    ATTEMPT_STARTED,
    ATTEMPT_COMPLETED,
    ATTEMPT_PROCESS_LOST,
    ATTEMPT_ABANDONED,
    ATTEMPT_DUPLICATE_SUPPRESSED,
    ATTEMPT_LATE_RESULT,
)

# ---------------------------------------------------------------------------------------
# Terminal statuses (D2 §14.2 named terminal mapping)
# ---------------------------------------------------------------------------------------
FINAL_STATUS_VALID = "VALID"
FINAL_STATUS_INVALID_SCHEMA = "INVALID_SCHEMA"
FINAL_STATUS_INVALID_BUSINESS = "INVALID_BUSINESS"
FINAL_STATUS_STALE_DECISION = "STALE_DECISION"
FINAL_STATUS_CAPACITY_BLOCKED = "CAPACITY_BLOCKED"

FINAL_STATUSES = (
    FINAL_STATUS_VALID,
    FINAL_STATUS_INVALID_SCHEMA,
    FINAL_STATUS_INVALID_BUSINESS,
    FINAL_STATUS_STALE_DECISION,
    FINAL_STATUS_CAPACITY_BLOCKED,
)

# ---------------------------------------------------------------------------------------
# Reason codes (D2 §14.2 mapping table, §18 failure matrix, §19 stale matrix)
# ---------------------------------------------------------------------------------------
REASON_VALID_PROVIDER_DECISION = "VALID_PROVIDER_DECISION"
REASON_REFUSAL = "REFUSAL"
REASON_AUTH_PERMISSION = "AUTH_PERMISSION"
REASON_TRANSPORT_FAILURE = "TRANSPORT_FAILURE"
REASON_PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
REASON_RATE_LIMIT = "RATE_LIMIT"
REASON_SCHEMA_FAILURE = "SCHEMA_FAILURE"
REASON_PARTIAL_RESULT = "PARTIAL_RESULT"
REASON_MALFORMED_OUTPUT = "MALFORMED_OUTPUT"
REASON_UNSUPPORTED_EVIDENCE = "UNSUPPORTED_EVIDENCE"
REASON_INVALID_REQUEST = "INVALID_REQUEST"
REASON_DEADLINE_EXPIRED = "DEADLINE_EXPIRED"
REASON_EVIDENCE_SUPERSEDED = "EVIDENCE_SUPERSEDED"
REASON_OPPORTUNITY_STALE = "OPPORTUNITY_STALE"
REASON_LATE_RESULT = "LATE_RESULT"
REASON_RETRY_EXHAUSTED = "RETRY_EXHAUSTED"
REASON_DUPLICATE_SUPPRESSED = "DUPLICATE_SUPPRESSED"
REASON_ADVISORY_QUEUE_REJECTED = "ADVISORY_QUEUE_REJECTED"  # D2 literal (§14.2)
REASON_ADVISORY_DB_CAPACITY_UNAVAILABLE = "ADVISORY_DB_CAPACITY_UNAVAILABLE"  # D2 §20.1 item 8
REASON_BINDING_INVALID_BEFORE_PROVIDER = "BINDING_INVALID_BEFORE_PROVIDER"
REASON_EXPERIMENT_CONFIG_MISMATCH_BEFORE_PROVIDER = "EXPERIMENT_CONFIG_MISMATCH_BEFORE_PROVIDER"
REASON_SHUTDOWN_BEFORE_PROVIDER = "SHUTDOWN_BEFORE_PROVIDER"  # D2 literal
REASON_SHUTDOWN_CANCELLED_ACTIVE_ATTEMPT = "SHUTDOWN_CANCELLED_ACTIVE_ATTEMPT"  # D2 literal

#: D2 §14.2 item 2 — the exhaustively enumerated terminals that may carry a NULL
#: `final_attempt_id`, because no provider Attempt ever existed. Frozen as a tuple and
#: mirrored by the `ck_advisory_invocation_no_attempt_reason` database CHECK.
NO_ATTEMPT_FINAL_PAIRS = (
    (FINAL_STATUS_STALE_DECISION, "DEADLINE_EXPIRED_BEFORE_PROVIDER"),
    (FINAL_STATUS_CAPACITY_BLOCKED, REASON_ADVISORY_QUEUE_REJECTED),
    (FINAL_STATUS_CAPACITY_BLOCKED, REASON_ADVISORY_DB_CAPACITY_UNAVAILABLE),
    (FINAL_STATUS_STALE_DECISION, "EVIDENCE_SUPERSEDED_BEFORE_PROVIDER"),
    (FINAL_STATUS_STALE_DECISION, "OPPORTUNITY_STALE_BEFORE_PROVIDER"),
    (FINAL_STATUS_STALE_DECISION, "ACTIVATION_DISABLED_BEFORE_PROVIDER"),
    (FINAL_STATUS_STALE_DECISION, REASON_BINDING_INVALID_BEFORE_PROVIDER),
    (FINAL_STATUS_STALE_DECISION, REASON_EXPERIMENT_CONFIG_MISMATCH_BEFORE_PROVIDER),
    (FINAL_STATUS_INVALID_SCHEMA, "SHUTDOWN_BEFORE_PROVIDER"),
)

REASON_DEADLINE_EXPIRED_BEFORE_PROVIDER = "DEADLINE_EXPIRED_BEFORE_PROVIDER"
REASON_CAPACITY_BLOCKED = "CAPACITY_BLOCKED"
REASON_EVIDENCE_SUPERSEDED_BEFORE_PROVIDER = "EVIDENCE_SUPERSEDED_BEFORE_PROVIDER"
REASON_OPPORTUNITY_STALE_BEFORE_PROVIDER = "OPPORTUNITY_STALE_BEFORE_PROVIDER"
REASON_ACTIVATION_DISABLED_BEFORE_PROVIDER = "ACTIVATION_DISABLED_BEFORE_PROVIDER"

# ---------------------------------------------------------------------------------------
# Experiment / arm vocabulary (D2 §13.1, §13.2 — frozen by PRE-01A-D1)
# ---------------------------------------------------------------------------------------
BASELINE_POLICY_VERSION = "ALL_ELIGIBLE_LONG_SHADOW_V1"  # D2 literal
BASELINE_ARM_LABEL = "WITHOUT_AI_BASELINE"  # D2 literal
TREATMENT_ARM_LABEL = "REAL_AI_TREATMENT"  # D2 literal

#: PRE-01A-D1: the placement this experiment owns. Advisory only, Trade Decision only.
EXPERIMENT_PLACEMENT_TRADE_DECISION = "C_TRADE_DECISION"

# ---------------------------------------------------------------------------------------
# Hash domains and version literals (D2 §12.1, §12.2)
# ---------------------------------------------------------------------------------------
# D2 §12.1 names these five domains verbatim.
ADVISORY_SNAPSHOT_ID_DOMAIN = "advisory-snapshot-v1"
ADVISORY_PAIR_ID_DOMAIN = "pre01a-pair-v1"
ADVISORY_ARM_ID_DOMAIN = "pre01a-arm-v1"
ADVISORY_INVOCATION_ID_DOMAIN = "advisory-invocation-v1"
ADVISORY_ATTEMPT_ID_DOMAIN = "advisory-attempt-v1"
ADVISORY_FINAL_DECISION_ID_DOMAIN = "advisory-final-v1"

# Implementation-frozen domains for the remaining derivations (§12.2).
ADVISORY_SNAPSHOT_PAYLOAD_HASH_DOMAIN = "pre01b-advisory-snapshot-payload-hash-v1"
ADVISORY_EXPERIMENT_DEFINITION_DIGEST_DOMAIN = "pre01b-experiment-definition-digest-v1"
ADVISORY_EXPERIMENT_ID_DOMAIN = "pre01b-experiment-id-v1"
ADVISORY_SEED_DIGEST_DOMAIN = "pre01b-advisory-seed-digest-v1"
ADVISORY_CONFIG_EPOCH_ID_DOMAIN = "pre01b-advisory-config-epoch-id-v1"
ADVISORY_PROMPT_DIGEST_DOMAIN = "pre01b-advisory-prompt-digest-v1"

# Implementation-frozen version literals carried by the derivations and the seed.
ADVISORY_SNAPSHOT_CONTRACT_VERSION = "pre01b-advisory-snapshot-payload-v1"
ADVISORY_BINDING_VERSION = "pre01b-advisory-input-binding-v1"
ADVISORY_EXPERIMENT_DEFINITION_VERSION = "pre01a-experiment-definition-v1"
ADVISORY_SEED_VERSION = "pre01b-advisory-seed-v1"
ADVISORY_DEADLINE_POLICY_VERSION = "pre01a-absolute-deadline-v1"
ADVISORY_CONFIG_EPOCH_VERSION = "pre01b-advisory-config-epoch-v1"
ADVISORY_PROMPT_VERSION = "pre01a-trade-decision-prompt-v1"
ADVISORY_SCHEMA_VERSION = "pre01a-trade-decision-schema-v1"
ADVISORY_TREATMENT_VERSION = "pre01a-real-ai-treatment-v1"

#: The complete frozen version-literal set, so an I2 reviewer audits one list rather than
#: a set of scattered string literals (D2 §12.2 requirement).
FROZEN_VERSION_LITERALS = {
    "snapshot_contract_version": ADVISORY_SNAPSHOT_CONTRACT_VERSION,
    "binding_version": ADVISORY_BINDING_VERSION,
    "experiment_definition_version": ADVISORY_EXPERIMENT_DEFINITION_VERSION,
    "seed_version": ADVISORY_SEED_VERSION,
    "deadline_policy_version": ADVISORY_DEADLINE_POLICY_VERSION,
    "config_epoch_version": ADVISORY_CONFIG_EPOCH_VERSION,
    "prompt_version": ADVISORY_PROMPT_VERSION,
    "schema_version": ADVISORY_SCHEMA_VERSION,
    "treatment_version": ADVISORY_TREATMENT_VERSION,
    "baseline_policy_version": BASELINE_POLICY_VERSION,
}

# ---------------------------------------------------------------------------------------
# Stale dimensions (D2 §19) — six independent dimensions, never collapsed into one boolean
# ---------------------------------------------------------------------------------------
STALE_EVIDENCE_REVISION_SUPERSEDED = "EVIDENCE_REVISION_SUPERSEDED"
STALE_OPPORTUNITY_ELIGIBILITY_LOST = "OPPORTUNITY_ELIGIBILITY_LOST"
STALE_MARKET_FRESHNESS_LOST = "MARKET_FRESHNESS_LOST"
STALE_BINDING_INVALID = "BINDING_INVALID"
STALE_EXPERIMENT_CONFIG_MISMATCH = "EXPERIMENT_CONFIG_MISMATCH"
STALE_DEADLINE_EXPIRED = "DEADLINE_EXPIRED"

STALE_DIMENSIONS = (
    STALE_EVIDENCE_REVISION_SUPERSEDED,
    STALE_OPPORTUNITY_ELIGIBILITY_LOST,
    STALE_MARKET_FRESHNESS_LOST,
    STALE_BINDING_INVALID,
    STALE_EXPERIMENT_CONFIG_MISMATCH,
    STALE_DEADLINE_EXPIRED,
)
