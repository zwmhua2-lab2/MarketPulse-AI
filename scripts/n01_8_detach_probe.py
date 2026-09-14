"""N01-8 detached-survival probe worker (validation-only, disposable workload).

Purpose: satisfy task section 18 *before* the 12 h clock is allowed to start.  It is deliberately
NOT the runtime supervisor -- it does no repository work at all.  It only proves, with artifacts,
that a process started through `scripts/n01_8_detach.py` keeps running after

  * the agent-side launcher returns,
  * the invoking shell command returns, and
  * a *different* agent/shell session reads the artifacts back,

and that stdout / stderr / progress JSONL / completion state are all persisted and re-readable.

Artifacts under --out-dir:
    progress.jsonl  one line per second: seq / pid / ppid / monotonic / wall clock
    stdout.txt      a line per 10 samples
    stderr.txt      a line per 7 samples
    status.json     {"state": "RUNNING"|"DONE"|"FAILED", ...} rewritten every sample
    final.json      written once on exit with the terminal state
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--seconds", type=float, default=90.0)
    args = parser.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    progress = out / "progress.jsonl"
    status = out / "status.json"
    started = time.monotonic()
    started_wall = _now()

    def state(name: str, seq: int) -> dict:
        return {
            "state": name,
            "pid": os.getpid(),
            "ppid": os.getppid(),
            "seq": seq,
            "started_wall": started_wall,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "argv": sys.argv,
        }

    _write_json(status, state("RUNNING", 0))
    seq = 0
    code = 0
    try:
        while True:
            elapsed = time.monotonic() - started
            seq += 1
            with progress.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "seq": seq,
                            "pid": os.getpid(),
                            "ppid": os.getppid(),
                            "at": _now(),
                            "elapsed_seconds": round(elapsed, 3),
                        }
                    )
                    + "\n"
                )
            if seq % 10 == 0:
                print(f"[probe] seq={seq} pid={os.getpid()} elapsed={elapsed:.1f}", flush=True)
            if seq % 7 == 0:
                print(f"[probe-stderr] seq={seq} pid={os.getpid()}", file=sys.stderr, flush=True)
            _write_json(status, state("RUNNING", seq))
            if elapsed >= args.seconds:
                break
            time.sleep(1.0)
    except BaseException as exc:  # noqa: BLE001 - the terminal state must survive any exit
        code = 1
        print(f"[probe] FAILED {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        _write_json(status, state("FAILED", seq))
        _write_json(
            out / "final.json",
            {**state("FAILED", seq), "error": f"{type(exc).__name__}: {exc}"},
        )
        return code
    _write_json(status, state("DONE", seq))
    _write_json(out / "final.json", {**state("DONE", seq), "exit_code": 0})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
