# 2026-09-18 PRE-01B-I2 Resume-01 — Advisory Durable Slice

## FINAL-02-FIX-01 Repair Checkpoint Evidence

- Task: `PRE-01B-I2-RESUME-01-C3-FINAL-02-FIX-01`.
- State: `IMPLEMENTING`; Implementation Completion Marker = `NOT READY`; Ready For
  Independent Review = `NO`; Human Acceptance = `NOT PERFORMED`.
- Scope was limited to P1-01 canonical PostgreSQL lock serialization and P1-02
  queue-only / no-Protection-reserve queue rejection handling. No migration, model,
  config, contract, provider, Gate, or Live activation change was made.

### Repairs

- P1-01: `append_evidence_revision()` locks predecessor Evidence N with `FOR UPDATE`,
  revalidates the current head while N remains locked, then appends N+1. Advisory
  Attempt start, finalizer, recovery/shutdown, and pre-Attempt terminal paths use the
  canonical Evidence -> Invocation -> exact Attempt order where an Attempt exists.
- P1-02: `post_commit_offer()` now performs only `put_nowait` plus immediate boolean
  reporting. Queue rejection terminalization is a separate `terminal_write_transaction`
  operation under Advisory capacity A; it does not borrow Protection reserve R. Initial,
  retry, and recovery re-offer false results are explicitly terminalized when A is
  available; otherwise prior durable state remains unchanged.

### Executable evidence

- Real PostgreSQL 16.15 lock-race tests prove both orders: writer-first holds Evidence N
  and finalizer waits before `EVIDENCE_SUPERSEDED`; finalizer-first holds Evidence then
  waits on a separately held Invocation while the N+1 writer waits on Evidence. Attempt
  start and PROCESS_LOST recovery similarly prove Evidence -> Invocation and
  Evidence -> Invocation -> Attempt respectively.
- Queue tests prove initial and recovery queue-full terminalization, retry-gap
  NULL-final-attempt behavior, zero Protection-R consumption, and retained durable state
  when terminal-write A capacity is unavailable.
- Schema verifier at `127.0.0.1:5450`: `60/60 PASS`, single head `20260917_0010`.
- Focused PRE-I2 / SE-02B / RuntimeHost: `160 passed, 1 warning`.
- Compatibility regression (PRE-I2, SE-02A/B, Product System, G5-2/3/4):
  `286 passed, 3 warnings`.
- Full backend at `127.0.0.1:5450`: `786 passed, 3 warnings`, exit 0. Shared
  `127.0.0.1:5432` and Production were not touched.

### Changed paths

- `backend/src/marketpulse/edge/repository.py`
- `backend/src/marketpulse/advisory/attempts.py`
- `backend/src/marketpulse/advisory/worker.py`
- `backend/src/marketpulse/advisory/ingress.py`
- `backend/src/marketpulse/g2/runtime.py`
- `backend/tests/test_pre_01b_i2_advisory_identity.py`
- `backend/tests/test_se_02b_opportunity_capture.py`
- `PROJECT_STATE.md`
- this log

### Execution timing

- Started: `2026-09-19T00:09:01.4762216+08:00`.
- Verification completed: `2026-09-19T00:55:13.6420480+08:00`.
- Estimate: `01:15:00–02:30:00`; measured end-to-end duration remains subject to final
  pre-commit remote revalidation and checkpoint creation.

### Remaining

- Perform the required final static/scope/remote revalidation, then create and push only
  the repair checkpoint if refs remain unchanged. This is not a final candidate or an
  authorization for independent review or Human Acceptance.
