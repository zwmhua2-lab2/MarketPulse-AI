# R2 timings (wall clock, 2026-10-20, UTC+8)

Evidence: file mtimes in `research/`, the two `family2_*` stamps, and the
`Measure-Command` run. Model thinking time between tool calls is included in
the spans; per-step stopwatches were not used.

| step | span | duration | what actually happened |
| --- | --- | --- | --- |
| 1 data | 23:07 → 23:35 | **28 min** | smoke test, serial fetch too slow (200 req / 4 min), rewrote to 8-thread chunked pool, full pull, integrity check, one full re-pull |
| 2 kernel | 23:11 → 23:17 | **~6 min** | `kernel.py` + `families.py` (family 1) + `test_parity.py` |
| 3 split / --confirm | 23:17 → 23:19 | **~2 min** | 70/30 slice + append-only `confirm_log.txt`, inside `kernel.py` |
| 4 family 2 | 23:25:09 → 23:25:21 | **12.2 s** | 12-line function + 1 registry line; `kernel.py` untouched |

## Blockers

1. **OKX latency ~1.2 s/request.** The serial 100-bars-per-call loop needed
   ~40 min per coin. Fixed with 36 chunks/coin × 8 workers behind one global
   8 req/s limiter → ~5 min per coin.
2. **Chunk-boundary off-by-one.** `after=cursor` is exclusive, so each chunk
   dropped the bar exactly at its own end: 35 gaps per coin, spaced exactly one
   chunk-span (20.83 days) apart. Only visible because `integrity.py` compares
   against the 5-minute grid. Fixed (`after=cursor+1`) and re-pulled: 0 gaps.
3. No blocked-for-half-a-day stop was triggered.

## Cost of one more family

12 seconds of writing, zero kernel changes, zero test changes. The expensive
part is inventing a hypothesis that is worth the 4-second run, not wiring it in.
