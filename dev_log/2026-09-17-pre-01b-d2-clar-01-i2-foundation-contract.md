# PRE-01B-D2-CLAR-01｜I2 Foundation Contract Clarification

## Task

Resolve exactly two design blockers found by the PRE-01B-I2 Foundation Integrity Gate:

1. B-01 — no-provider Attempt terminal reason contract.
2. F-01/F-02 — canonical arm-ID derivation/domain and exact future test contract.

Task type: `ACCEPTED-CONTRACT CLARIFICATION / DOCS ONLY`.

## Scope

- Clarify D2 §14.2 no-Attempt terminal whitelist and exact status/reason pairs.
- Align queue-capacity and Advisory DB-capacity terminal mappings.
- Freeze `baseline_arm_id` / `treatment_arm_id` derivation and arm domain/version literal.
- Add directly dependent future I2 acceptance wording.

## Out of Scope

- No implementation, migration, model, test, Runtime, config, schema, service or database change.
- No I2 continuation, provider/model selection, provider call or Gate A/B/C activation.
- No `PROJECT_STATE.md`, `AI_CONTEXT.md`, `DECISIONS.md` or product requirement change.
- No change to PRE-01A-D1, PRE-01B-D1, foundation history, `main`, `.workbuddy`, memory or skills.
- No Independent Review, Human Acceptance or merge to `main`.

## Repository Truth

- Protocol remote `main`: `a80c55b7451f77883d8b0713a228f0d9bebf7d22`.
- Protocol: `v1.1.0 / ACCEPTED`.
- Project remote `main`: `547095f6705ce651272363676e2a2b51a66bb8b6`.
- Clarification task base: exact Accepted Main `547095f6705ce651272363676e2a2b51a66bb8b6`.
- Foundation branch: `pre-01b-i2-advisory-ingress-core`.
- Foundation checkpoint: `b0b89a8919303bbbd34b4e7c685282e95e0c73ed`.
- Clarification branch: `design/pre-01b-d2-clar-01-i2-foundation-contract`.
- Root checkout had unrelated pre-existing dirty changes; work used an isolated worktree and did not
  reset, stash, clean, overwrite or attribute those changes.

## B-01 Evidence

Accepted D2 §14.2 allowed NULL `final_attempt_id` only for a reason whitelist containing
`CAPACITY_BLOCKED`. That token is a `final_status`, not a reason code. The same D2 artifact requires:

- queue full: `CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED`, no Attempt;
- Advisory DB capacity unavailable:
  `CAPACITY_BLOCKED / ADVISORY_DB_CAPACITY_UNAVAILABLE`, no provider Attempt.

Foundation evidence at `b0b89a8` copied the ambiguous list into vocabulary, ORM CHECK and migration
0010, so both required capacity pairs were rejected when `final_attempt_id` was NULL. Foundation tests
also asserted the ambiguous list verbatim. These files were read only and were not modified.

## B-01 Decision

`final_status` and `final_reason_code` are separate vocabularies. NULL `final_attempt_id` is legal and
required only for these exact closed-world pairs:

| `final_status` | `final_reason_code` |
|---|---|
| `STALE_DECISION` | `DEADLINE_EXPIRED_BEFORE_PROVIDER` |
| `CAPACITY_BLOCKED` | `ADVISORY_QUEUE_REJECTED` |
| `CAPACITY_BLOCKED` | `ADVISORY_DB_CAPACITY_UNAVAILABLE` |
| `STALE_DECISION` | `EVIDENCE_SUPERSEDED_BEFORE_PROVIDER` |
| `STALE_DECISION` | `OPPORTUNITY_STALE_BEFORE_PROVIDER` |
| `STALE_DECISION` | `ACTIVATION_DISABLED_BEFORE_PROVIDER` |
| `INVALID_SCHEMA` | `SHUTDOWN_BEFORE_PROVIDER` |

The exact no-Attempt reason whitelist is therefore the seven reason codes in the right column.
`CAPACITY_BLOCKED` is removed as a reason and remains only a status. No wildcard capacity meaning and
no fabricated Attempt are allowed.

## B-01 Compatibility

- D2 §14.2 terminal authority, §18 failure matrix, §20.1 DB capacity semantics and §27 acceptance
  wording now use the same queue/DB capacity reasons.
- Existing Attempt-origin constraints remain unchanged for all terminals that have an Attempt.
- Because I2 is unaccepted and unmerged, its final descendant candidate may correct migration 0010
  directly. A second Alembic revision is not required solely to preserve the candidate mistake.
- This clarification changes no migration.

## F-01 Evidence

D2 §12.1 wrote `H(pair_id, arm_label)`. Foundation `identity.py` called
`canonical_digest(ADVISORY_PAIR_ID_DOMAIN, pair_id, arm_label)`, making the effective canonical
preimage `['pre01a-pair-v1', pair_id, arm_label]`. That is deterministic but not the literal D2
formula and reuses the pair semantic domain. The foundation test only proved the two arm results differ
and that labels are fixed; it did not independently prove the domain/preimage.

## F-01 Options Considered

- Option A — dynamic `pair_id` as hash domain: rejected because it has no fixed/versioned arm domain.
- Option B — dedicated fixed/versioned arm domain: selected for explicit semantic domain separation,
  versionability, canonical serialization and deterministic replay.
- Option C — reuse pair domain: rejected because pair and arm identity classes would share one semantic
  domain and arm derivation would lack an independent version authority.

## F-01 Decision

Freeze:

```text
arm_id = H("pre01a-arm-v1", pair_id, arm_label)
baseline_arm_id = H("pre01a-arm-v1", pair_id, "WITHOUT_AI_BASELINE")
treatment_arm_id = H("pre01a-arm-v1", pair_id, "REAL_AI_TREATMENT")
```

Exact canonical JSON preimages are:

```json
["pre01a-arm-v1", "<pair_id>", "WITHOUT_AI_BASELINE"]
["pre01a-arm-v1", "<pair_id>", "REAL_AI_TREATMENT"]
```

`pre01a-arm-v1` is the frozen arm hash domain/version literal. The decision keeps the existing
cryptographic collision-resistance assumption while preventing cross-identity-class domain aliasing and
providing an explicit future version boundary.

## F-02 Future Test Requirement

Future I2 tests must independently construct the expected canonical JSON preimage/digest and assert the
exact domain literal, `pair_id`, label and input order. Merely asserting baseline/treatment inequality, or
using the implementation under test to compute the expected value, is insufficient.

## Files Changed

Exactly two repository paths:

1. `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`
2. `dev_log/2026-09-17-pre-01b-d2-clar-01-i2-foundation-contract.md`

## Verification

- Realtime project/protocol refs checked against the task pins.
- Complete D2 token inventory performed for `CAPACITY_BLOCKED`, queue/DB capacity reasons,
  `final_attempt_id`, arm IDs, pair domain and arm-domain wording.
- Foundation vocabulary/identity/model/migration/test evidence inspected read-only at `b0b89a8`.
- `git diff --check`: PASS (exit 0; Windows LF-to-CRLF notices only, no whitespace error).
- Exact delta: PASS — exactly the two authorized repository paths.
- Conflict-marker scan: PASS — none found.
- Final ref/branch and remote push checks are recorded in the completion report.
- Tests: `ZERO` by task contract; no test code changed or executed.
- Production/Runtime/Schema/Migration/Config: `ZERO`.

## Result

`PRE-01B-D2-CLAR-01 = DESIGN CLARIFICATION CANDIDATE`.

Status: `READY FOR INDEPENDENT REVIEW` after commit and push complete.
This is not Human Acceptance and does not amend Accepted D2 on `main`.

## Remaining

- Independent Review.
- Human Acceptance if review passes.
- Only after separate authorization: resume I2 continuation and apply the clarified contract to the
  unaccepted foundation candidate.

## Context For Next AI

- Treat this branch as docs-only clarification evidence.
- Do not edit migration 0010 or foundation code during clarification review.
- Review B-01 as exact status/reason pairs, not a reason-only open set.
- Review F-01 against the exact canonical preimage and dedicated `pre01a-arm-v1` domain.
- Original PRE-01B-D2 on Accepted Main remains the last Human-Accepted design until this candidate is
  independently reviewed and Human-accepted.

## Evidence Pointers

- Accepted D2: §12.1, §12.2, §14.2, §16, §18, §20.1, §27.
- PRE-01A-D1: §6.3, §8, §10, §13, AC-09/21/22/23.
- Foundation read-only evidence at `b0b89a8`:
  `backend/src/marketpulse/advisory/vocabulary.py`,
  `backend/src/marketpulse/advisory/identity.py`,
  `backend/src/marketpulse/db/models.py`,
  `backend/alembic/versions/20260917_0010_advisory_ingress_core.py`,
  `backend/tests/test_pre_01b_i2_advisory_identity.py`.
