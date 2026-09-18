# UI-V1-D01-AMEND-01-PERSIST｜Amendment 落库

## Result

- Task type: `ACCEPTED AMENDMENT REPOSITORY PERSISTENCE / DOCS + STATE ONLY`.
- Result: `UI-V1-D01-AMEND-01-PERSIST-FIX-01 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW` for Amendment repository-persistence finding closure only.
- Human-confirmed Amendment: `UI-V1-D01-AMEND-01 = ACCEPTED / FROZEN`.
- Formal artifact: `docs/design/UI-V1/UI-V1-D01-AMEND-01-Post-Freeze-Amendment.md`.

## Scope and State Reconciliation

- Persisted the accepted CR-01 through CR-06 contracts without implementing a CR code fix.
- `UI-V1-D01 = ACCEPTED / FROZEN — AS AMENDED BY UI-V1-D01-AMEND-01`.
- `UI-RD01 = ACCEPTED / FROZEN — AS AMENDED BY UI-V1-D01-AMEND-01`.
- `UI-RD01-I01 = ACCEPTED / COMPLETE` is preserved; `I02–I05 = NOT STARTED / NOT AUTHORIZED`.
- CR-01 and CR-02: contract accepted; current Foundation implementation remediation = `REQUIRED / NOT STARTED`.
- CR-03: contract accepted; current implementation remediation = `NOT APPLICABLE YET`; future OpportunityTraceRead implementation must comply.
- CR-04: contract accepted; current implementation remediation = `NOT APPLICABLE YET`; future EdgeAggregateRead implementation must comply.
- CR-05: contract accepted; current shared Product Read contract remediation = `REQUIRED / NOT STARTED`. `UI-RD01-I01` historically remains `ACCEPTED / COMPLETE` and has already implemented `backend/src/marketpulse/api/product/models.py::TraceNodeState`, whose current enum lacks `NOT_YET_DUE`. The later post-freeze CR-05 contract requires remediation; it does not revoke or downgrade I01 acceptance. Future OpportunityTraceRead / trace consumers must comply.
- CR-06: contract accepted; current implementation remediation = `NOT APPLICABLE YET`; future EdgeAggregateRead implementation must comply.

## Boundaries

- Production code, tests, schema, migrations, indexes, runtime/configuration, dependencies, and
  `PRODUCT_REQUIREMENTS.md` are `ZERO CHANGE`.
- Original frozen UI-V1-D01 and UI-RD01 artifacts are not rewritten.
- No UI-RD01-I02–I05, UI-I01–UI-I06, PRE-01B-I2, Real AI, live G2→G3, Gate, or Live work starts.

## Verification

- Task-base diff and allowed-file inventory are checked before handoff.
- `git diff --check` is required and recorded in the task result.
