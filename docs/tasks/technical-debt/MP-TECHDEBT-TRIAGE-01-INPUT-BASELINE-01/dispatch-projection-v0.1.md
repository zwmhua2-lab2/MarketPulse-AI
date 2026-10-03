# Derived dispatch projection — ready for separate dispatch

Canonical authority: `task-contract-v0.1.json`; this projection grants no independent authority. Subject: `NOT_STARTED`. Formalization completion is not Subject execution.

Exact input identities:

```json
{
  "canonical_contract": {
    "path": "docs/tasks/technical-debt/MP-TECHDEBT-TRIAGE-01-INPUT-BASELINE-01/task-contract-v0.1.json",
    "git_blob_sha1": "ed3f8814561972220df4080f7476efb2e887762c",
    "bytes": 36397,
    "sha256": "611e917cb23d8b3825a110ee8da826f1f15d2ae23678b7a0cdb0a1982b563175"
  },
  "resolved_execution_profile": {
    "path": "docs/tasks/technical-debt/MP-TECHDEBT-TRIAGE-01-INPUT-BASELINE-01/resolved-execution-profile-v0.1.json",
    "git_blob_sha1": "1abdcd270ae1b94d89d27022d6c29ac844c9ef3f",
    "bytes": 2997,
    "sha256": "afb17b1563e64d55cfec877021950a4e27ccc81d8e5f50abe7a26a7f0feff018"
  }
}
```

Resolved target: ER-3 / GPT-6.1 Sol / Medium / Codex Desktop. Actual Subject runtime: `NOT_RUN`.

Before execution use these exact canonical/profile identities and their currentness/eligibility conditions. The original pending registration/profile wording below is recovery history resolved by those exact records. All original permissions, tools, gates, stop conditions, AC01–AC22 and downstream boundaries remain binding.

<!-- CANONICAL SUBJECT BEGIN -->
# MarketPulse-AI
# MP-TECHDEBT-TRIAGE-01-INPUT-BASELINE-01 v0.1

Contract State:

`STRUCTURED TASKCONTRACT CANDIDATE`

Formal Registration:

`NOT YET FORMALLY REGISTERED`

Dispatch State:

`NOT YET DISPATCHABLE`

Task Type:

`READ_ONLY_INVESTIGATION`

Workline:

`Technical Debt`

---

# 1. IDENTITY

## Task ID

`MP-TECHDEBT-TRIAGE-01-INPUT-BASELINE-01`

## Task Version

`v0.1`

## Work Name

`Technical Debt Authoritative Input Baseline Completion`

## Project

`MarketPulse-AI`

## Product Repository

`zwmhua2-lab2/MarketPulse-AI`

## Repository Baseline

Authoritative ref:

`origin/main`

Contract-creation SHA:

`8c94ea338f500e2ea4dd2f8a5ccc81a65502468e`

Binding Mode:

`EXACT BASELINE / REBIND ON DRIFT`

If execution-time `origin/main` differs from the SHA above:

`TASK = STALE / STOP / REBIND REQUIRED`

Do not silently substitute the newer main.

## Governance Repository

`zwmhua2-lab2/ai-dev-workflow`

## Governance Baseline

`cbc1a221646a9f4703a65e626e58cf192ed96426`

## Parent Workline

`MP-TECHDEBT-TRIAGE-01`

## Formal Parent Contract

`NONE PROVEN`

The historical Triage tasks predate the current formalization of this successor and are retained as historical evidence.

## Lineage

1. `MP-TECHDEBT-TRIAGE-01 v0.1`
   - Result: `BLOCKED`
   - Cause: mandatory MarketPulse inputs incomplete.

2. `MP-TECHDEBT-TRIAGE-01-RERUN-01 v0.1`
   - Result: `BLOCKED`
   - Cause: mandatory inputs still incomplete; Parallel Guard / per-ref proof incomplete.

3. Current:
   - `MP-TECHDEBT-TRIAGE-01-INPUT-BASELINE-01 v0.1`
   - Purpose: isolate and close the evidence-input problem before Technical Debt substantive analysis resumes.

---

# 2. GOVERNANCE

## Governance Version

`0.1.0`

## Rule Pack Version

`0.1.0`

## Manifest Identity

`fd00-rule-manifest/0.1.0`

## Governance Mode

`SELF_HOSTED`

## Active Execution Profile

`EMRP-1.1`

## Role

`Investigator / Evidence Collector`

## Task Mode

`STRICT READ_ONLY`

## Risk Tier

`L2`

Rationale:

- cross-subsystem evidence;
- authority/currentness analysis;
- parallel-work interaction;
- DB / migration / runtime / Product Read evidence navigation;
- uncertainty remains.

No lower risk tier is assumed merely because repository mutation is prohibited.

## Risk Tags

- `PERSISTENCE`
- `MIGRATION`
- `TRANSACTION`
- `RECOVERY`

These tags describe evidence surfaces under inspection.

They do not authorize mutation of those subsystems.

## Parent Tier Floor

`L2 CONSERVATIVE FLOOR FOR THIS TASK`

No lower formal parent tier has been proven.

## Protected Subsystem

`NO DIRECT MUTATION`

Observed protected/relevant surfaces may include:

- database / migration infrastructure;
- runtime;
- Product Read;
- TradingAuditRead;
- test infrastructure;
- persistence/recovery.

## Authoritative Inputs

### Governance

Must freshly load from the exact/current authorized Workflow baseline:

- `AI_WORKFLOW_BOOTSTRAP.md`
- `governance/WORKFLOW_RULE_MANIFEST.md`
- all six `REQUIRED_ACTIVE` rules
- complete Workflow `PROJECT_STATE.md`
- ACTIVE `EXECUTION_MODEL_ROUTING_PROFILE.md`

### MarketPulse

Must use Repository Truth and locate/read, as applicable:

- `PROJECT_STATE.md`
- `AI_CONTEXT.md`
- `PRODUCT_REQUIREMENTS.md`
- `DECISIONS.md`
- `AGENTS.md`
- current accepted/frozen requirement artifacts relevant to A–H
- accepted review / verification / closeout records relevant to A–H
- relevant `dev_log` records
- exact Git identities associated with those records.

### Supplemental Navigation Only

Historical external reports from:

- `MP-TECHDEBT-TRIAGE-01 v0.1`
- `MP-TECHDEBT-TRIAGE-01-RERUN-01 v0.1`

may be used only to locate evidence.

They do not override Repository Truth.

## Frozen Truth Identity

`NO SINGLE NEW FROZEN TRUTH CREATED BY THIS TASK`

Existing accepted/frozen artifacts retain their own identities.

## Amendments

`NONE`

## Required Gates

1. Rule Load
2. Exact Repository Binding
3. Duplication / Parallel Guard
4. START Ref Snapshot
5. Authoritative Input Completion
6. A–H Navigation Map
7. END Ref Snapshot
8. Ref Diff
9. Self-check
10. Technical Debt Workline Completion Review

No Fix / Implementation / Acceptance Gate is authorized.

## Role Separation

This Investigator:

- may collect evidence;
- may classify evidence completeness;
- may not implement fixes;
- may not close debt;
- may not grant implementation authorization;
- may not accept product changes.

---

# 3. BOUNDARY

## Scope

This task exists solely to establish a reliable:

`AUTHORITATIVE_INPUT_BASELINE`

for subsequent Technical Debt investigation.

It MUST:

1. establish exact MarketPulse and Workflow repository bindings;
2. establish complete start/end Git ref snapshots;
3. establish a Parallel Occupancy Baseline;
4. fully read the bounded authoritative document inputs;
5. resolve A–H historical finding lineage/navigation;
6. identify the exact source/test/config/migration areas that future technical evidence collection must inspect;
7. produce an authoritative input manifest;
8. produce a structured result envelope.

## A–H Navigation Targets

These are navigation targets only, not current Triage conclusions.

### A

`N01-7-R01-RR-P2-01`

Memory Operational Watch / Bounded Retention Growth.

### B

`IR-01-NBF-02`

TradingAuditRead in-memory `O(n²)` intent-side lookup.

Historical accepted performance observation includes approximately 18.2 s large-request evidence.

This task MUST NOT turn that historical observation into a current performance/SLA conclusion.

### C

Test DB isolation / shared PostgreSQL test-environment constraint, including relevant:

`TEST-ISO-01`

and successor/current evidence.

### D

Alembic URL precedence / `DATABASE_URL` interaction, including the historical PRE-01B-I1:

`RR-P2-01`

and related current evidence.

### E

Development dependency evidence concerning:

`aiosqlite`

including the current/historical `requirements-dev.txt` finding.

### F

`R04-P2-01`

### G

`SE02C-R7`

### H

All other current `OPEN / REMAINS / DEFERRED` items that fall within the Technical Debt inventory after deduplication.

H does not authorize an unbounded repository-wide audit.

## Out of Scope

This task MUST NOT:

- perform substantive A–H Technical Debt disposition;
- assign fix priority;
- assign final severity;
- close findings;
- repair findings;
- optimize performance;
- change source code;
- change tests;
- change dependency manifests;
- change lock files;
- change migrations;
- change schema;
- modify a database;
- call Real AI/Product Provider APIs;
- run paid provider workloads;
- alter Runtime configuration;
- create implementation branches;
- create Fix candidates;
- grant Fix authorization;
- perform Official Product Verification;
- perform Human Acceptance;
- change Gate state.

## Allowed Actions

READ_ONLY only:

- `git status`
- `git rev-parse`
- `git show`
- `git log`
- `git branch`
- `git worktree list`
- `git for-each-ref`
- `git ls-remote`
- `git diff` without mutation
- filesystem read
- source/config/test path discovery
- bounded full-file reads
- GitHub/remote read-only metadata
- repository-external evidence generation.

## Forbidden Actions

Forbidden:

- edit repository files;
- create repository files;
- stage;
- commit;
- push;
- branch creation;
- tag creation;
- ref mutation;
- reset;
- rebase;
- clean;
- stash mutation;
- merge;
- cherry-pick;
- package install;
- package upgrade;
- lockfile regeneration;
- DB write;
- migration execution that changes state;
- provider invocation;
- service/runtime mutation.

## Allowed Changes

Repository:

`NONE`

DB:

`NONE`

Runtime:

`NONE`

Dependencies:

`NONE`

Git refs:

`NONE`

Repository-external evidence package:

`ALLOWED`

## Workspace Boundary

Both repositories are READ_ONLY:

- `zwmhua2-lab2/MarketPulse-AI`
- `zwmhua2-lab2/ai-dev-workflow`

Existing dirty worktrees must be preserved exactly.

Do not clean or normalize them.

## Stop Conditions

STOP and return structured `BLOCKED` if:

1. Rule Load cannot be fully completed.
2. Contract baseline differs from live authority without authorized Rebind.
3. Required authority cannot be resolved.
4. Required bounded document cannot be fully read.
5. output truncation cannot be repaired by bounded range reading.
6. required ref snapshot cannot be completed.
7. parallel activity makes evidence identity unreliable.
8. execution discovers that repository mutation is necessary.
9. scope needs to expand into substantive Technical Triage.
10. secrets or credentials would need to be read.
11. Product Provider/API invocation would be required.
12. current Task ID already exists as a newer Formal Task or completed successor.

---

# 4. EXECUTION

## Profile Requirements

Minimum Capability:

`Cross-document authority reasoning + Git/ref analysis + bounded cross-subsystem evidence navigation`

## Routing Recommendation

Execution Routing Tier:

`ER-3`

Recommended Model:

`GPT-6.1 Sol`

Recommended Reasoning:

`Medium`

Recommended Harness:

`Codex Desktop`

## Resolved Execution Profile

`PENDING FORMAL REGISTRATION / NOT YET RESOLVED`

## Actual Runtime Model

`NOT_RUN`

The Executor must record the actual model/harness/effort separately.

## Provider Constraints

Execution AI provider is determined by the resolved execution profile.

Product/MarketPulse external AI provider calls:

`PROHIBITED`

## Tools

Allowed:

- local Git read-only tooling;
- filesystem read-only tooling;
- shell commands with no mutation;
- GitHub read-only metadata where required.

## Permissions

`READ_ONLY`

No `WRITE_MAIN`.

No repository write permission is conferred by this contract.

## Data Policy

- do not open `.env` for secret values;
- do not read API keys/tokens;
- do not print credentials;
- only inspect existence/configuration structure where necessary and non-secret;
- do not transmit repository secrets to external services.

## Context Requirement

`FRESH CONTEXT`

At execution start:

1. load current Workflow Rules completely;
2. resolve exact repository truth;
3. load this exact TaskContract identity;
4. ignore stale chat conclusions as authority;
5. use historical reports only as navigation.

## Budget

Repository write budget:

`0`

Database mutation budget:

`0`

External Product Provider calls:

`0`

Paid external workload:

`0`

Fix rounds:

`0`

Implementation attempts:

`0`

Task dispatch attempts:

`1`

A `BLOCKED` result does not authorize automatic whole-task rerun.

A new successor/rebind must be designed if the blocker is material.

## Full-Read Protocol

For every document required as `FULLY_READ`, first establish:

- exact repository;
- exact ref;
- exact path;
- blob SHA;
- byte size when available;
- line count when available.

Then read bounded ranges until coverage is:

`LINE 1 → FINAL LINE`

Search fragments, grep output, file headers, previews, or truncated shell output do not count as full reads.

## Recovery Behavior

If one read is truncated:

- continue with bounded range reads;
- do not restart the whole task.

If authority remains unresolved after bounded inspection:

- record exact unresolved item;
- STOP;
- return `BLOCKED`.

---

# 5. REPOSITORY / REF BASELINE CONTRACT

## START_REF_SNAPSHOT

Before substantive input analysis, capture complete local ref state including:

- `refs/heads/*`
- `refs/remotes/origin/*`
- `refs/tags/*`
- `refs/codex/*`

For every ref capture:

- full ref name;
- object SHA.

Special attention:

`refs/codex/turn-diffs/*`

Do not record only a count.

## END_REF_SNAPSHOT

At completion, capture the same namespace again.

Produce exact classification:

- `ADDED`
- `REMOVED`
- `MOVED`
- `UNCHANGED`

If provenance/owner cannot be proven:

`OWNER_UNVERIFIED`

Do not infer ownership from naming.

---

# 6. PARALLEL OCCUPANCY CONTRACT

Build:

`PARALLEL_OCCUPANCY_MAP`

Inspect current evidence for potential overlap with at least:

- UI-I01 / System
- UI-RD01-I04 / EdgeAggregateRead
- Frontend Lint Foundation
- Real AI Activation preparation
- Product Read
- TradingAuditRead
- Runtime / Test Harness
- DB / Migration
- dependency/tooling work.

For each observed workline use only:

- `OBSERVED_ACTIVE`
- `OBSERVED_INACTIVE`
- `UNKNOWN`

An empty PR list is not proof that parallel work does not exist.

No chat-memory occupancy claim may substitute for repository/local evidence.

---

# 7. AUTHORITATIVE INPUT MANIFEST

Produce:

`AUTHORITATIVE_INPUT_MANIFEST`

Minimum fields:

| Field | Requirement |
|---|---|
| Input ID | stable local identifier |
| Repository | exact repository |
| Authority Ref | exact ref/SHA |
| Path | exact path |
| Blob SHA | required where applicable |
| Bytes / Lines | record where available |
| Read Coverage | exact bounded coverage |
| Status | allowed enum below |
| Relevance | A–H / governance / project context |
| Lineage | predecessor/successor where applicable |

Allowed Status:

- `FULLY_READ`
- `NOT_REQUIRED`
- `NOT_FOUND`
- `AUTHORITY_UNRESOLVED`
- `BLOCKED`

A successful task MUST contain:

`PARTIAL = 0`

---

# 8. REQUIRED DOCUMENT BASELINE

At minimum resolve and fully read the current authoritative versions of:

1. `PROJECT_STATE.md`
2. `AI_CONTEXT.md`
3. `PRODUCT_REQUIREMENTS.md`
4. `DECISIONS.md`
5. `AGENTS.md`

Then locate and read only bounded, relevant accepted/frozen records for A–H.

Do NOT read every historical file in the repository.

Do NOT read the entire source tree.

This task is an input-baseline task, not the Technical Evidence task.

---

# 9. A–H EVIDENCE NAVIGATION MAP

Produce:

`AH_EVIDENCE_NAVIGATION_MAP`

Required columns:

| Debt | Historical ID | Current Repository Record | Accepted/Frozen Authority Link | Review/Verification Link | Candidate Technical Area | Technical Evidence Still Required |
|---|---|---|---|---|---|---|

This map MUST NOT assign:

- current severity;
- fix priority;
- final currentness verdict;
- final reproducibility verdict;
- final fix scope.

Those belong to later Technical Evidence / Triage tasks.

---

# 10. HISTORICAL PERFORMANCE BOUNDARY

The historical TradingAuditRead observation:

- large request approximately `18.2 s`;
- transaction hold approximately `18.1 s`;
- 16 SQL statements;
- DB query-per-row `NOT OBSERVED`;

must remain classified during this task as:

`HISTORICAL OBSERVATION`

unless current evidence from a separately authorized verification proves otherwise.

This task MUST NOT execute a new performance workload merely to reproduce it.

Do not create a performance SLA.

---

# 11. VERIFICATION / ACCEPTANCE

## Verification Contract

Verification Profile Identity:

`MP-TECHDEBT-INPUT-BASELINE-VP-v0.1`

State:

`CONTRACT-LOCAL CANDIDATE / EFFECTIVE ONLY WITH THIS TASKCONTRACT`

Verification is limited to deterministic evidence-completeness and no-mutation checks.

## Required Verification Assets

1. `AUTHORITATIVE_INPUT_MANIFEST`
2. `START_REF_SNAPSHOT`
3. `END_REF_SNAPSHOT`
4. `REF_DIFF`
5. `PARALLEL_OCCUPANCY_MAP`
6. `AH_EVIDENCE_NAVIGATION_MAP`
7. `NO_MUTATION_EVIDENCE`
8. structured completion report.

## Acceptance Criteria

### AC01
Workflow Rule Load = PASS.

### AC02
MarketPulse exact execution-time `origin/main` identified.

### AC03
Workflow exact execution-time `origin/main` identified.

### AC04
Contract baseline currentness established.

### AC05
Local checkout state distinguished from remote authority.

### AC06
Complete START ref snapshot captured.

### AC07
Complete END ref snapshot captured.

### AC08
Added / Removed / Moved / Unchanged ref diff computed.

### AC09
Parallel Occupancy Map completed.

### AC10
Current `PROJECT_STATE.md` fully read.

### AC11
Current `AI_CONTEXT.md` fully read.

### AC12
Current `PRODUCT_REQUIREMENTS.md` fully read.

### AC13
Current `DECISIONS.md` fully read.

### AC14
Current `AGENTS.md` fully read.

### AC15
Relevant accepted/frozen A–H authority records located and bounded reading completed.

### AC16
A–H Evidence Navigation Map completed.

### AC17
Authoritative Input Manifest contains zero `PARTIAL`.

### AC18
No substantive Technical Debt disposition performed.

### AC19
Repository / DB / dependency / runtime / refs mutation = `NONE`.

### AC20
No Product Provider / paid performance workload executed.

### AC21
Historical 18.2 s evidence has not been upgraded into a current SLA/performance verdict.

### AC22
Structured Result Envelope completed.

## Required Review

After successful execution:

`TECHNICAL DEBT WORKLINE COMPLETION REVIEW REQUIRED`

This review checks only whether the Evidence Baseline satisfies this contract.

It does not accept or reject any Technical Debt fix.

## Independent Reviewer

`NOT REQUIRED BY THIS READ_ONLY CONTRACT BY DEFAULT`

If an authority conflict, contradictory accepted record, or material evidence-lineage dispute is discovered:

`ESCALATE / INDEPENDENT REVIEW REQUIRED BEFORE CONSUMPTION`

## Human Gate

`NONE FOR READ_ONLY EVIDENCE COLLECTION`

Human decision is required if:

- scope expansion is needed;
- authority conflict cannot be mechanically resolved;
- a later Fix / Implementation Task is proposed.

## Acceptance Predicate

Task completion may be declared only if:

- AC01–AC22 all PASS;
- all required evidence is current;
- no required input remains partial;
- exact baseline is valid;
- repository mutation is NONE;
- no unresolved stop condition exists.

---

# 12. RESULT CONTRACT

## Allowed Result Status

Success:

`AUTHORITATIVE_INPUT_BASELINE_COMPLETE`

with:

`READY_FOR_TECHNICAL_EVIDENCE_TASK_DESIGN`

Blocked:

`BLOCKED`

Stale:

`STALE / REBIND_REQUIRED`

No other success wording is allowed.

## Subject Candidate

`NONE`

This task investigates Repository Truth; it does not produce a product candidate.

## Produced Candidate

`NONE`

## Changed Scope

Expected:

`NONE`

## Repository Mutation

Required:

`NONE`

## Self-check

Required:

`PASS / FAIL`

with evidence.

## Official Verification

`NOT_APPLICABLE TO PRODUCT CANDIDATE`

Do not write Official Verification PASS.

## Review

At Executor completion:

`NOT_PERFORMED / PENDING WORKLINE COMPLETION REVIEW`

## Acceptance

Must remain:

`NOT PRODUCT ACCEPTANCE`

## Findings

Report:

- authority gaps;
- stale/superseded records;
- unresolved lineage;
- ref movement;
- parallel occupancy;
- missing technical evidence.

Do not repair findings.

## Remaining Work

Success case:

`TECHNICAL EVIDENCE COLLECTION TASK DESIGN`

Blocked case:

only the minimum successor required to remove the blocker.

## Evidence References

All evidence must identify exact:

- repository;
- ref/SHA;
- path;
- blob/object identity where applicable;
- external evidence artifact path.

## Staleness

If bound repository/governance truth changes before the result is consumed:

`RESULT = STALE FOR DOWNSTREAM GATING`

Revalidation or Rebind is required.

---

# 13. REQUIRED STRUCTURED RESULT ENVELOPE

The Executor must return:

## Result Status

## Contract Identity

## Dispatch Identity

## Run Identity

## Repository Bindings

## Governance Binding

## Start Ref Snapshot Summary

## End Ref Snapshot Summary

## Ref Diff

## Parallel Occupancy

## Authoritative Input Manifest

## A–H Evidence Navigation Map

## Repository Mutation

## Self-check

## Official Verification

## Review

## Acceptance

## Findings

## Remaining Work

## Evidence References

## Staleness

## AC01–AC22 Matrix

---

# 14. EVIDENCE PACKAGE

Repository-external evidence package may contain:

- `INPUT_BASELINE_RESULT.md`
- `AUTHORITATIVE_INPUT_MANIFEST.json`
- `START_REF_SNAPSHOT.txt`
- `END_REF_SNAPSHOT.txt`
- `REF_DIFF.txt`
- `PARALLEL_OCCUPANCY_MAP.md`
- `AH_EVIDENCE_NAVIGATION_MAP.md`
- `NO_MUTATION_EVIDENCE.txt`
- `STRUCTURED_RESULT_ENVELOPE.json`

These artifacts are execution evidence.

They do not become Repository Truth merely because they exist outside Git.

---

# 15. SUCCESS BOUNDARY

Successful completion permits only:

`READY_FOR_TECHNICAL_EVIDENCE_TASK_DESIGN`

The likely next Task ID is:

`MP-TECHDEBT-TRIAGE-01-TECH-EVIDENCE-01`

but this contract DOES NOT:

- create that task;
- authorize that task;
- dispatch that task;
- perform its work.

---

# 16. FINAL STOP

After emitting the Structured Result Envelope:

`STOP`

Do NOT automatically continue into:

- `TECH-EVIDENCE-01`
- substantive A–H Triage
- Disposition Review
- Fix Design
- Fix Implementation
- Verification
- Integration
- Acceptance.
<!-- CANONICAL SUBJECT END -->

<!-- RESOLVED PROFILE BEGIN -->
```json
{
  "profile_id": "MP-TECHDEBT-TRIAGE-01-INPUT-BASELINE-01-REP-v0.1",
  "subject_task_id": "MP-TECHDEBT-TRIAGE-01-INPUT-BASELINE-01",
  "subject_task_version": "v0.1",
  "canonical_contract_identity": {
    "path": "docs/tasks/technical-debt/MP-TECHDEBT-TRIAGE-01-INPUT-BASELINE-01/task-contract-v0.1.json",
    "git_blob_sha1": "ed3f8814561972220df4080f7476efb2e887762c",
    "bytes": 36397,
    "sha256": "611e917cb23d8b3825a110ee8da826f1f15d2ae23678b7a0cdb0a1982b563175"
  },
  "profile_authority": {
    "profile": "EMRP-1.1",
    "repository": "zwmhua2-lab2/ai-dev-workflow",
    "commit": "cbc1a221646a9f4703a65e626e58cf192ed96426",
    "path": "governance/profiles/EXECUTION_MODEL_ROUTING_PROFILE.md",
    "git_blob_sha1": "99f00b5809d0104e326282e12041e2a9ca2db467",
    "bytes": 9412,
    "sha256": "6eaeb5cc301b85f101d778e0a5785fa7d93b9dd86944fb4480911aaff8741d01"
  },
  "recommended": {
    "routing_tier": "ER-3",
    "provider": "OpenAI",
    "model": "GPT-6.1 Sol",
    "model_id": "gpt-6.1-sol",
    "reasoning": "Medium",
    "harness": "Codex Desktop"
  },
  "resolved": {
    "routing_tier": "ER-3",
    "provider": "OpenAI",
    "model": "GPT-6.1 Sol",
    "model_id": "gpt-6.1-sol",
    "reasoning": "Medium",
    "mapped_effort": "medium",
    "harness": "Codex Desktop",
    "context": "FRESH CONTEXT",
    "permissions": "READ_ONLY"
  },
  "eligibility_evidence": {
    "authorization": "Human-dispatched RERUN-01 explicitly authorizes resolving this exact Subject route; does not dispatch Subject execution.",
    "binding": "Exact remote main + active governance/version/profile verified.",
    "availability": "Current Codex Desktop tool metadata exposes gpt-6.1-sol with medium effort on local host.",
    "harness_effort_support": "mcp__codex_app create_thread/send_message_to_thread model and effort metadata lists gpt-6.1-sol and medium; no task created or messaged.",
    "minimum_capability": "Cross-document authority reasoning + Git/ref analysis + bounded cross-subsystem evidence navigation; matches exact A1 requirement.",
    "sufficiency": "ER-3 Medium is explicitly bound by A1 and RERUN-01 for substantive bounded cross-document authority and Git/ref reasoning; EMRP ER-3 allows Medium.",
    "hard_eligibility": "PASS; read-only Git/filesystem tools available, fresh context required, L2 retained, Product Provider prohibited.",
    "selection_method": "Hard Eligibility -> Minimum Capability -> Static Preference -> First Sufficient",
    "fallback": "NONE; no alias/substitution; no model exhaustion.",
    "revalidation": "Before Subject dispatch, revalidate baseline/governance currency, model availability, harness/effort and exact contract/profile identities; stop on mismatch."
  },
  "actual_runtime": {
    "model": "NOT_RUN",
    "provider": "NOT_RUN",
    "harness": "NOT_RUN",
    "reasoning": "NOT_RUN",
    "subject_state": "NOT_STARTED"
  },
  "product_provider_calls": "PROHIBITED",
  "write_main": "PROHIBITED",
  "scope_change": "NONE"
}
```
<!-- RESOLVED PROFILE END -->
