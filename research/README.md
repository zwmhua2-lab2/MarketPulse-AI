# research/ — offline hypothesis sandbox (R2/R3)

Falsify a K-line hypothesis per coffee break, without touching `backend/`, the
database, Docker, migrations or the Gate workflow.

## Boundary — sandbox vs production

- **Writable scope is `research/` only.** Never touch `backend/`, `frontend/`,
  the production database, migrations, Docker, or production wiring.
- Research tasks **do not** have to walk the production Group / Gate / Issue /
  PR / cross-model-QA chain. They do have to state: scope, time box, how the
  result is self-checked, and where the real evidence lives.
- Research is for falsification, not for tuning. Do not adjust a family,
  window, cost or threshold to make a gate pass. Do not use a doc update or an
  audit result to back-tune a family.
- Pending items N1–N3 are tracked in `NOW.md` only; this file does not restate
  their status.

## Exploration vs confirmation

- Any data that took part in choosing a family, comparing parameters or judging
  direction is **exploration data**.
- The current `data/{COIN}_5m.csv` (730 days) has already been looked at, so it
  is exploration; `--confirm` refuses to run on it by design.
- **Confirmation may only use data accumulated after this point and never used
  for any selection**, with the window and the criterion agreed before it starts.
- Pulling in earlier history now only **extends exploration**. It does not
  become a confirmation set, even if that history has never been inspected.

## History — do not overwrite

`integrity_report.txt`, `cost_breakdown.txt`, `run_confirm.txt`,
`run_explore.txt`, `run_r3_explore.txt`, `data_availability.txt`,
`test_registry.json` and `confirm_log.txt` are historical evidence. Append new
runs as new files or new rows; never rewrite, truncate or "tidy" the existing
records.

## Layout

| file | role |
| --- | --- |
| `fetch_data.py` | OKX `/api/v5/market/history-candles` downloader (always sends `User-Agent`; 100 bars/request, 8 threads, ~8 req/s) |
| `data/{COIN}_5m.csv` | local bars, git-ignored |
| `integrity.py` | duplicates / missing bars / continuity / regime coverage → `integrity_report.txt` |
| `kernel.py` | forward returns, baseline, paired block bootstrap, two gates, Bonferroni `m`, 6 horizons |
| `families.py` | one function per family + the `FAMILIES` registry |
| `cost_breakdown.py` | fee / slippage / cross-term split and baseline = drift − cost |
| `data_availability.py` | read-only probes: what free derivatives data exists, how deep, how fine |
| `test_parity.py` | pins the copied cost model to `marketpulse.edge.forward`, no-lookahead, block length, gate logic |
| `test_registry.json` | every distinct comparison ever evaluated; `m` = its length, never reset |
| `confirm_log.txt` | R2 log, kept as history (the 730d file is exploration only since R3) |

## Contract

* family = `f(df) -> bool Series`; signal is read at bar close.
* entry = **next** bar open, exit = close of bar `i + horizon`.
* horizons: 5m / 15m / 1h / 4h / 12h / 1d (`30s` is `n/a`, the data is 5m).
* cost = production SPOT long round trip: 5 bps slippage each side + 10 bps fee
  each side, multiplicative → **29.96 bps**.
* baseline = unconditional net forward mean of every bar in the same
  coin / horizon / window.
* blocks = whole UTC days, never shorter than the horizon (1d uses 5-day blocks).
* two gates, both at the Bonferroni level `alpha / m`:
  * **G1** delta (event − baseline) CI lower > 0 → the signal carries information;
  * **G2** net expectancy CI lower > 0 → the trade makes money after cost.
* `n_blocks < 30` → `样本不足`.

## Adding a family

1. write the function in `families.py`,
2. add one line to `FAMILIES`,
3. `python kernel.py`.

Nothing in `kernel.py` changes; the new rows raise `m` automatically and every
row in that run is judged at the new, stricter level.

## Usage

```bash
python fetch_data.py --days 730          # ~10 min (36 chunks x 8 workers)
python integrity.py
python cost_breakdown.py
python kernel.py                         # all 730 days, exploration only
python kernel.py --horizons 5m,1d --boot 5000
python -m unittest test_parity -v
python data_availability.py              # ~15 requests, stores nothing
```

`--confirm` refuses by design: the 730-day file has been looked at and is
exploration by policy. A real confirmation window needs **data accumulated
after this point and never used for selection**. Earlier history pulled in now
only extends exploration — it does not become a confirmation set.

## Known limits

K-lines only: no taker side, no liquidations, no open interest, no historical
order book. `panic_drop_long` uses "sharp drop + volume expansion" as a proxy
for forced selling; it is not a liquidation detector. See
`data_availability.txt` for what free derivatives data actually exists.
