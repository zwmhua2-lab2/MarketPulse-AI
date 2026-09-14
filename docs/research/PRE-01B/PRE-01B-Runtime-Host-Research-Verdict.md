# PRE-01B — Runtime Host Research Verdict

Status:
RESEARCH VERDICT / DESIGN INPUT
READY FOR FORMAL DESIGN

---

## 6.1 Repository Verdict

- N01 overall = ACCEPTED / COMPLETE
- Integrated Runtime Host = NOT STARTED
- N01 Acceptance does not prove Integrated Runtime Host
- live Opportunity → G3 = NOT WIRED
- current FastAPI app does not own complete runtime lifecycle
- current production composition root not found
- production market-state accessors for bbo_for/state_version_for require Formal Design treatment
- DB engine/session ownership + disposal require Formal Design treatment
- Memory P2 remains NON-BLOCKING / REMAINS

## 6.2 External Research Verdict

Frozen:

- FastAPI / Starlette lifespan
  = STRONG REUSE CANDIDATE
  for application-scoped composition / startup / shutdown / cleanup.

- Python asyncio / AnyIO structured concurrency
  = STRONG REUSE CANDIDATE
  for task ownership / cancellation / bounded concurrency primitives.

But it must be stated explicitly:

- TaskGroup
  != automatic restart supervisor

- FastAPI lifespan
  != OS process/service supervisor

- OS process supervision
  = separate deployment / operational boundary

- WinSW / Windows Service mechanisms
  = REFERENCE CANDIDATE for that future boundary,
  not automatically part of Integrated Runtime Host V1.

## 6.3 Framework Verdict

Frozen:

No new generic Python runtime framework
is currently justified.

Must not introduce:

- Celery
- Redis
- Kafka
- Kubernetes
- LangGraph
- generic agent runtime
- new trading framework
- generic workflow engine

unless a future new Accepted Requirement provides real requirement evidence.

## 6.4 Formal Design Required Questions

D1 must adjudicate:

1. composition root ownership
2. FastAPI lifespan 与 Integrated Runtime Host 的责任边界
3. DB engine/sessionmaker ownership + disposal
4. production latest BBO/state-version access boundary
5. G2 Opportunity → G3 explicit handoff
6. AI bounded invocation:
   - absolute deadline
   - cancellation
   - retry ownership
7. task ownership / supervision / failure policy
8. graceful startup/shutdown ordering
9. backpressure isolation: AI/non-safety work cannot block Protection
10. runtime health/readiness semantics
11. restart-safe duplicate/late completion fencing
12. Memory P2 observation inputs without changing its accepted threshold/status
13. what explicitly remains outside Integrated Runtime Host V1:
    OS service/deployment supervision unless separately approved
