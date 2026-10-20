# Timings (wall clock, 2026-10-20 / -21, UTC+8)

Evidence: file mtimes in `research/`, the `family2_*` stamps, `Measure-Command`.
Model thinking time between tool calls is included; per-step stopwatches were
not used.

## R2 (2026-10-20)

| step | span | duration | what actually happened |
| --- | --- | --- | --- |
| 1 data | 23:07 → 23:35 | **28 min** | smoke test, serial fetch too slow (200 req / 4 min), rewrote to 8-thread chunked pool, full pull, integrity check, one full re-pull |
| 2 kernel | 23:11 → 23:17 | **~6 min** | `kernel.py` + `families.py` (family 1) + `test_parity.py` |
| 3 split / --confirm | 23:17 → 23:19 | **~2 min** | 70/30 slice + append-only `confirm_log.txt` |
| 4 family 2 | 23:25:09 → 23:25:21 | **12.2 s** | 12-line function + 1 registry line; `kernel.py` untouched |

Blockers: OKX latency ~1.2 s/request; `after=cursor` off-by-one dropped one bar
per chunk (35 fake gaps) until `integrity.py` caught it.

## R3 (2026-10-21)

| step | span | duration | what actually happened |
| --- | --- | --- | --- |
| kernel upgrade | 01:05 → 01:07 | **~2 min** | gross/net split, two gates, `m` registry, 6 horizons, block length per horizon |
| family C | 01:07 | **~1 min** | 12-line `squeeze_breakout` + 1 registry line |
| cost breakdown | 01:08 | **~1 min** | `cost_breakdown.py`, 12 rows of drift vs cost |
| data availability | 01:09 → 01:12 | **~3 min** | ~20 read-only probes, HEAD only for dumps, nothing stored |
| 36-row table | 01:07 / 01:12 | **66 s cold, 24 s warm** | 50,000 bootstrap x 36 rows; cold run pays for the rolling 5-day quantile |
| tests | — | **0.55 s** | 11 tests |

## Cost of one more family

12 s of writing, zero kernel changes, zero test changes. The expensive part is
inventing a hypothesis worth the 24-second run, not wiring it in.
