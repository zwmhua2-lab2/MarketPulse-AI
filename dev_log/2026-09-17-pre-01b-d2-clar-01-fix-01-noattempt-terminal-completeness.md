# PRE-01B-D2-CLAR-01-FIX-01｜No-Attempt Terminal Completeness Fix

## Task

Fix exactly the two blocking findings from the PRE-01B-D2-CLAR-01 Independent Review:

1. `PRE01B-D2-CLAR01-RR-P1-01` — deadline reason contradiction.
2. `PRE01B-D2-CLAR01-RR-P1-02` — incomplete no-Attempt stale/invariant/config pair set.

Task type: `CLARIFICATION FIX / DOCS ONLY`.

## Scope

- Freeze durable Attempt existence as the deadline/provenance boundary.
- Inventory every Invocation-exists/no-Attempt terminal path in the current artifact.
- Freeze one complete exact `(final_status, final_reason_code)` no-Attempt pair set.
- Synchronize D2 §14, §17, §18, §19 and §27.
- Preserve CLAR-01 capacity reasons and F-01/F-02 arm-domain/test requirements.

## Out of Scope

- No implementation, migration, schema, test, Runtime, config, service, database or provider change.
- No PRE-01B-I2 resume; no migration 0010, `vocabulary.py` or `identity.py` edit.
- No arm-ID, SAVEPOINT, DB-fence, retry, RuntimeHost, Gate A/B/C or PRE-01A redesign.
- No Real AI/provider selection/call, Production/Live activation or Human Acceptance.
- No `PROJECT_STATE.md`, `AI_CONTEXT.md`, `DECISIONS.md`, `PRODUCT_REQUIREMENTS.md`, PRE-01A-D1,
  PRE-01B-D1, prior CLAR-01 dev log, `.workbuddy`, memory, skills or daily-log change.
- No merge/rebase/reset/amend/force-push and no modification of CLAR-01/foundation branches.

## Repository Truth

- Protocol: `v1.1.0 / ACCEPTED`.
- Protocol remote `main`: `a80c55b7451f77883d8b0713a228f0d9bebf7d22` (live `git ls-remote`).
- Project remote `main`: `2c95cc21cc99d85c5692c5f9b276c5805cc32b13` (live `git ls-remote`).
- Original accepted PRE-01B-D2 closeout base: `547095f6705ce651272363676e2a2b51a66bb8b6`.
- Reviewed parent candidate/branch:
  `design/pre-01b-d2-clar-01-i2-foundation-contract@f583e096d3a9ed33dcce97b6581b8c336a57d671`.
- Parent of reviewed candidate: `547095f6705ce651272363676e2a2b51a66bb8b6`.
- I2 foundation checkpoint: `b0b89a8919303bbbd34b4e7c685282e95e0c73ed`.
- Fix branch:
  `design/pre-01b-d2-clar-01-fix-01-noattempt-completeness`, created from exact `f583e096...`.
- Root checkout contained unrelated pre-existing dirty changes. Work was performed in an isolated
  external worktree; no root change was reset, stashed, cleaned, overwritten or attributed to this task.

## Main Drift Classification

`git log` / `git diff --name-status 547095f6..2c95cc21` independently showed four UI-V1 commits
touching only UI-V1 design/dev logs plus `AI_CONTEXT.md`, `DECISIONS.md` and `PROJECT_STATE.md`;
the targeted PRE-01A/PRE-01B/advisory/foundation semantic-path diff was empty. The drift is therefore
orthogonal to PRE-01A/PRE-01B/I2 foundation semantics. Live remote `main` still equals the dispatch pin. The
clarification lineage therefore remains based on immutable `f583e096...`; no rebase or main merge was
performed.

## Reviewed Parent Candidate

The actual candidate artifact and parent dev log were inspected at `f583e096...`. CLAR-01 correctly
separated queue and DB capacity reasons and froze the dedicated `pre01a-arm-v1` domain, but its
seven-pair no-Attempt set was incomplete and §17.2 contradicted §14.2/§18.

## Independent Review Findings

- P1-01 reproduced: §14.2/§18 used `DEADLINE_EXPIRED_BEFORE_PROVIDER` when no Attempt existed,
  while §17.2 still said enqueue/dequeue/before-call expiry used `DEADLINE_EXPIRED`.
- P1-02 reproduced: §19 named six stale dimensions, but §14.2/§18 did not freeze exact no-Attempt
  pairs for Decision Snapshot/input-binding invalid and enabled-but-incompatible experiment/config.
  The internal-invariant row also left implementation to invent a terminal mapping.

## P1-01 Root Cause

The artifact mixed three non-equivalent signals: lifecycle phase name, network-call count and durable
Attempt provenance. In particular, the Attempt-start-committed/provider-I/O-not-started race had no
single authoritative classification.

## P1-01 Fix

Durable Attempt existence is now the only boundary:

- no Attempt row ever committed ⇒
  `STALE_DECISION / DEADLINE_EXPIRED_BEFORE_PROVIDER`, NULL Attempt/Decision, zero provider;
- same-Invocation Attempt committed ⇒
  `STALE_DECISION / DEADLINE_EXPIRED`, same-Invocation `final_attempt_id` required;
- Attempt-start commit followed by deadline expiry before provider I/O still uses the Attempt-exists
  mapping. Zero network calls do not authorize a `*_BEFORE_PROVIDER` reason.

## P1-02 Root Cause

CLAR-01 enumerated capacity, deadline, supersede, opportunity, activation and shutdown terminals but
left binding integrity/config incompatibility under vague stale/internal-invariant wording. §19 also did
not map each stale dimension on both sides of durable Attempt creation.

## Complete No-Attempt Inventory

The whole artifact was searched for before-enqueue, queued, pre-claim, pre-Attempt, before-provider,
zero/no-provider, stale, binding/hash/snapshot, experiment/config, activation, capacity, shutdown,
deadline, supersede, freshness, eligibility and internal-invariant wording.

Invocation-exists/no-Attempt terminal classes are exactly:

1. deadline expired;
2. queue rejected;
3. Advisory DB capacity unavailable;
4. Evidence revision superseded;
5. Opportunity eligibility lost;
6. market freshness lost;
7. activation genuinely disabled;
8. immutable Decision Snapshot/input-binding invalid;
9. activation enabled but invocation-bound experiment/config definition mismatched;
10. shutdown terminal.

Opportunity eligibility and market freshness intentionally share one pair, leaving nine unique legal
pairs. Admission preparation failure has no Invocation and is outside this set. A DB/lock/fence failure
that cannot reliably commit terminal fields retains the prior durable state and is retried/recovered
under the original deadline; it is not an extra pair. Retry exhaustion/process loss/active shutdown
already have Attempt provenance and are also outside this set.

## Exact Closed-World Pair Table

§14.2 is the sole current normative authority:

| `final_status` | `final_reason_code` |
|---|---|
| `STALE_DECISION` | `DEADLINE_EXPIRED_BEFORE_PROVIDER` |
| `CAPACITY_BLOCKED` | `ADVISORY_QUEUE_REJECTED` |
| `CAPACITY_BLOCKED` | `ADVISORY_DB_CAPACITY_UNAVAILABLE` |
| `STALE_DECISION` | `EVIDENCE_SUPERSEDED_BEFORE_PROVIDER` |
| `STALE_DECISION` | `OPPORTUNITY_STALE_BEFORE_PROVIDER` |
| `STALE_DECISION` | `ACTIVATION_DISABLED_BEFORE_PROVIDER` |
| `STALE_DECISION` | `BINDING_INVALID_BEFORE_PROVIDER` |
| `STALE_DECISION` | `EXPERIMENT_CONFIG_MISMATCH_BEFORE_PROVIDER` |
| `INVALID_SCHEMA` | `SHUTDOWN_BEFORE_PROVIDER` |

Every pair requires `final_attempt_id=NULL`, `final_decision_id=NULL` and provider calls `ZERO`.
The DB contract is implementable as `final_attempt_id IS NULL` iff the exact pair belongs to this set;
no status wildcard, reason-only wildcard or generic `CAPACITY_BLOCKED` reason is legal.

## New / Retained Reason Literals

New, narrowly scoped deterministic literals:

- `BINDING_INVALID_BEFORE_PROVIDER`: immutable snapshot/binding integrity is corrupted, invalid,
  misrouted or incompatible before any Attempt exists.
- `EXPERIMENT_CONFIG_MISMATCH_BEFORE_PROVIDER`: activation remains enabled, but the
  Invocation-bound experiment definition/config epoch is incompatible with current authority.

Retained unchanged: `DEADLINE_EXPIRED_BEFORE_PROVIDER`, `ADVISORY_QUEUE_REJECTED`,
`ADVISORY_DB_CAPACITY_UNAVAILABLE`, `EVIDENCE_SUPERSEDED_BEFORE_PROVIDER`,
`OPPORTUNITY_STALE_BEFORE_PROVIDER`, `ACTIVATION_DISABLED_BEFORE_PROVIDER`,
`SHUTDOWN_BEFORE_PROVIDER`, and all Attempt-origin diagnostics.

## §14 / §17 / §18 / §19 / §27 Synchronization

- §14.2: sole nine-pair authority, IFF CHECK, NULL Decision rule and Attempt-start race.
- §17.2: deadline classification now uses durable Attempt existence, never phase/network count.
- §18: every pre-Attempt stale/invariant/config path has an exact pair; non-terminalizable DB/fence
  failures explicitly retain prior durable state instead of inventing a reason.
- §19: all six stale dimensions now give exact no-Attempt and Attempt-exists behavior; enabled config
  mismatch is separate from genuinely DISABLED activation.
- §27: requires all legal pairs, near-miss rejection, deadline race, binding/config/freshness/eligibility,
  exact capacity/shutdown/supersede cases and NULL final Decision proof.

## F-01 / F-02 Non-Regression

Unchanged:

```text
baseline_arm_id = H("pre01a-arm-v1", pair_id, "WITHOUT_AI_BASELINE")
treatment_arm_id = H("pre01a-arm-v1", pair_id, "REAL_AI_TREATMENT")
```

Future tests must still independently construct the expected canonical digest/preimage; comparing arm
inequality or calling the implementation helper to build expected values remains insufficient.

## Files Changed

Exactly two repository paths:

1. `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`
2. `dev_log/2026-09-17-pre-01b-d2-clar-01-fix-01-noattempt-terminal-completeness.md`

## Verification

- Realtime protocol/project refs and candidate/foundation lineage checked.
- Whole-artifact required-token scan completed.
- §14/§17/§18/§19/§27 consistency reviewed against actual text.
- `git diff --check`: PASS (exit 0; Windows LF-to-CRLF warning only).
- Conflict-marker scan: PASS.
- Exact delta from `f583e096...`: PASS — one modified design doc and this one added dev log.
- Parent CLAR-01 branch, foundation branch and remote main: unchanged.
- Tests: ZERO by task contract; no test code changed or executed.
- Production/Runtime/Migration/Schema/Config/State docs: ZERO.

## Result

`PRE-01B-D2-CLAR-01-FIX-01 = FIX CANDIDATE DESIGN`.

Status: `READY FOR INDEPENDENT RE-REVIEW` after commit and push.
This is not Human Acceptance and does not amend Accepted D2 on `main`.

## Remaining

- Independent Re-Review.
- Human Acceptance only if re-review passes.
- PRE-01B-I2 remains not resumed and unauthorized by this task.

## Context For Next AI

- Review §14.2 as the sole no-Attempt whitelist authority and verify dependent sections only reference it.
- Treat durable Attempt-row existence, not network calls or phase names, as the provenance boundary.
- Inspect both new reason literals for their narrow semantic classes; do not widen them into a generic
  error taxonomy.
- Original accepted PRE-01B-D2 on main remains the last Human-Accepted design.

## Evidence Pointers

- Parent candidate: `f583e096...`, D2 §14.2, §17.2, §18, §19, §27.
- PRE-01A-D1 §6, §8, §9, §10 and future implementation AC.
- Parent CLAR-01 dev log:
  `dev_log/2026-09-17-pre-01b-d2-clar-01-i2-foundation-contract.md`.
- Foundation checkpoint `b0b89a89...` was read-only; no foundation file changed.
