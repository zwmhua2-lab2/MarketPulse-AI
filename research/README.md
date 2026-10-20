# research/ — offline hypothesis sandbox (R2)

Falsify a K-line hypothesis per coffee break, without touching `backend/`, the
database, Docker, migrations or the Gate workflow.

## Layout

| file | role |
| --- | --- |
| `fetch_data.py` | OKX `/api/v5/market/history-candles` downloader (always sends `User-Agent`; 100 bars/request, ~9 req/s) |
| `data/{COIN}_5m.csv` | local bars, git-ignored |
| `integrity.py` | duplicates / missing bars / continuity / regime coverage → `integrity_report.txt` |
| `kernel.py` | the whole evaluation kernel: forward returns, baseline, paired day-block bootstrap, 70/30 split, `--confirm` log |
| `families.py` | one function per family + the `FAMILIES` registry |
| `test_parity.py` | pins the copied cost model to `marketpulse.edge.forward`, plus no-lookahead tests |
| `confirm_log.txt` | append-only record of every `--confirm` run (timestamp + family version) |

## Contract

* family = `f(df) -> bool Series`; signal is read at bar close.
* entry = **next** bar open, exit = close of bar `i + horizon`.
* cost = production SPOT long round trip: 5 bps slippage each side + 10 bps fee
  each side, multiplicative.
* baseline = unconditional forward mean of every bar in the same coin /
  horizon / window.
* delta CI = paired day-block bootstrap, 10,000 resamples, UTC days as blocks.
* `n_days < 30` → `样本不足`.

## Adding a family

1. write the function in `families.py`,
2. add one line to `FAMILIES`,
3. `python kernel.py`.

## Usage

```bash
python fetch_data.py --days 730          # ~10 min, resumable per coin
python integrity.py
python kernel.py                         # exploration window (first 70%)
python kernel.py --confirm               # confirmation window, appended to confirm_log.txt
python -m unittest test_parity -v
```

## Known limits

K-lines only: no taker side, no liquidations, no open interest, no historical
order book. `panic_drop_long` uses "sharp drop + volume expansion" as a proxy
for forced selling; it is not a liquidation detector.
