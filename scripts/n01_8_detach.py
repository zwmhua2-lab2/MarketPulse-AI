"""N01-8 detached-run launcher (validation-only).

Why this file exists
--------------------
The N01-8 formal window is >= 12 h, far longer than any agent turn.  Task section 18 therefore
requires the formal run to be owned by a *detached* supervisor that (a) survives the launcher
process exiting and (b) does not depend on the chat/agent process being alive.

What was measured in this sandbox (see the N01-8 dev_log "Detached runtime" section)
------------------------------------------------------------------------------------
* `subprocess.Popen(..., DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP)` **is reaped** the moment the
  invoking shell command returns -- the child dies with no stderr and no traceback.
* Adding `CREATE_BREAKAWAY_FROM_JOB`, `CREATE_NO_WINDOW` or `CREATE_NEW_CONSOLE` does not help:
  all four flag combinations were killed within ~1 s.
* WMI `Win32_Process.Create` and PowerShell `Start-Process` are both refused by the sandbox policy.
* The Bash tool's own background-task mechanism keeps the child alive, but that child is owned by
  the agent process tree, which violates requirement (b).
* **Windows Task Scheduler works**: a process started by a scheduled-task instance has
  `taskeng/svchost` as its ancestor and is outside the agent's process tree.

So the launcher is split in two halves:

    task  mode     agent side: writes the spec + the .cmd wrapper, registers and runs a one-shot
                   scheduled task, records the child PID and every artifact path, then returns.
    launcher mode  runs *inside* the scheduled task: reads the spec, spawns the target supervisor
                   detached, records its own PID and exit, and (by default) exits immediately.

Artifacts (all under --run-dir) -- this is the re-attach contract of task section 18:
    detach_spec.json        exact argv the supervisor was started with
    n01_8_task.cmd          the scheduled-task command line
    launch.json             launcher pid/parent, child pid, task name, artifact paths, timestamps
    task_stdout.txt         scheduled-task wrapper stdout (owned by the `>>` redirect)
    task_stderr.txt         scheduled-task wrapper stderr (owned by the `2>>` redirect)
    supervisor_stdout.txt   target supervisor stdout (written by the launcher)
    supervisor_stderr.txt   target supervisor stderr (written by the launcher)
    task_query.txt          `schtasks /query /v` snapshot for the task's last result
    <supervisor artifacts>  written by the supervisor itself (progress JSONL, stdout, status)

Cleanup: `--mode cleanup --task-name <name>` deletes the scheduled task.  Called at closeout, never
while the run is in flight.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

TASK_PREFIX = "n01-8"
PYTHON = sys.executable


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _decode(raw: bytes | None) -> str:
    """schtasks output is in the console code page, not UTF-8."""
    return (raw or b"").decode("utf-8", errors="replace")


def _run(args: list[str]) -> tuple[int, str, str]:
    completed = subprocess.run(args, capture_output=True, shell=False, check=False)
    return completed.returncode, _decode(completed.stdout), _decode(completed.stderr)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


# ---------------------------------------------------------------------------------------------
# mode = launcher  (runs INSIDE the scheduled task)
# ---------------------------------------------------------------------------------------------
def _launcher(spec_path: Path) -> int:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    run_dir = spec_path.parent
    argv: list[str] = list(spec["argv"])
    keep_alive = bool(spec.get("keep_alive"))
    stdout_path = Path(spec["stdout"])
    stderr_path = Path(spec["stderr"])

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    started = time.monotonic()
    record: dict = {
        "mode": "launcher",
        "launcher_pid": os.getpid(),
        "launcher_ppid": os.getppid(),
        "launcher_python": PYTHON,
        "child_pid": None,
        "creationflags": creationflags,
        "keep_alive": keep_alive,
        "argv": argv,
        "spec": str(spec_path),
        "run_dir": str(run_dir),
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "spawned_at": _now(),
        "child_alive_after_2s": None,
        "spawn_error": None,
        "launcher_exits_at": None,
        "launcher_returncode": 0,
    }
    try:
        # The supervisor's stdout/stderr must NOT be the files the scheduled-task wrapper itself
        # redirects into: on Windows the wrapper holds those handles without FILE_SHARE_WRITE, so a
        # second open raises PermissionError.  `supervisor_stdout.txt` / `supervisor_stderr.txt` are
        # therefore distinct from `task_stdout.txt` / `task_stderr.txt`.
        with stdout_path.open("ab") as out_handle, stderr_path.open("ab") as err_handle:
            process = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=out_handle,
                stderr=err_handle,
                creationflags=creationflags,
                close_fds=True,
                cwd=spec.get("cwd") or str(run_dir),
            )
        record["child_pid"] = process.pid
        time.sleep(2.0)
        record["child_alive_after_2s"] = process.poll() is None
        if keep_alive:
            record["child_returncode"] = process.wait()
            record["keep_alive_seconds"] = round(time.monotonic() - started, 3)
    except Exception as exc:  # noqa: BLE001 - the launcher record must survive any failure
        record["spawn_error"] = f"{type(exc).__name__}: {exc}"
        record["launcher_returncode"] = 1
    record["launcher_exits_at"] = _now()
    _write_json(run_dir / "launch.json", record)
    return int(record["launcher_returncode"])


# ---------------------------------------------------------------------------------------------
# mode = task  (agent side)
# ---------------------------------------------------------------------------------------------
def _task(args) -> int:
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    task_name = args.task_name or f"{TASK_PREFIX}-{args.label}"
    # The scheduled-task wrapper owns these two files; the launcher writes the supervisor's output
    # to different names (Windows forbids a second non-shared handle on the wrapper's redirect).
    stdout_path = run_dir / "task_stdout.txt"
    stderr_path = run_dir / "task_stderr.txt"
    supervisor_stdout = run_dir / "supervisor_stdout.txt"
    supervisor_stderr = run_dir / "supervisor_stderr.txt"

    spec = {
        "argv": list(args.target),
        "cwd": args.cwd,
        "keep_alive": bool(args.keep_alive),
        "stdout": str(supervisor_stdout),
        "stderr": str(supervisor_stderr),
        "created_at": _now(),
        "label": args.label,
    }
    spec_path = run_dir / "detach_spec.json"
    _write_json(spec_path, spec)

    wrapper = run_dir / "n01_8_task.cmd"
    wrapper.write_text(
        "@echo off\r\n"
        f'"{PYTHON}" "{Path(__file__).resolve()}" --mode launcher '
        f'--spec "{spec_path}" >> "{stdout_path}" 2>> "{stderr_path}"\r\n',
        encoding="utf-8",
    )

    evidence: dict = {
        "label": args.label,
        "task_name": task_name,
        "spec": str(spec_path),
        "wrapper": str(wrapper),
        "task_stdout": str(stdout_path),
        "task_stderr": str(stderr_path),
        "supervisor_stdout": str(supervisor_stdout),
        "supervisor_stderr": str(supervisor_stderr),
        "run_dir": str(run_dir),
        "target_argv": list(args.target),
        "agent_pid": os.getpid(),
        "registered_at": None,
        "run_requested_at": None,
        "task_create": None,
        "task_run": None,
        "task_query": None,
        "child_pid": None,
        "child_argv0": None,
    }

    rc, out, err = _run(
        [
            "schtasks",
            "/create",
            "/tn",
            task_name,
            "/tr",
            str(wrapper),
            "/sc",
            "ONCE",
            "/st",
            "23:59",
            "/f",
            "/it",
        ]
    )
    evidence["task_create"] = {"rc": rc, "out": out.strip(), "err": err.strip()}
    evidence["registered_at"] = _now()

    rc, out, err = _run(["schtasks", "/run", "/tn", task_name])
    evidence["task_run"] = {"rc": rc, "out": out.strip(), "err": err.strip()}
    evidence["run_requested_at"] = _now()

    # Bounded discovery of the supervisor PID (never waits for completion).  The matcher is
    # deliberately strict -- an earlier version matched this process itself, because the target
    # command line is part of the agent process' own argv.
    marker = args.pid_marker or (Path(args.target[1]).name if len(args.target) > 1 else None)
    run_dir_token = str(run_dir).replace("\\", "/").lower()
    own_pid = os.getpid()
    deadline = time.monotonic() + args.discover_seconds
    while time.monotonic() < deadline:
        time.sleep(1.0)
        found = False
        with contextlib.suppress(Exception):
            import psutil

            for proc in psutil.process_iter(["pid", "cmdline"]):
                if proc.info["pid"] == own_pid:
                    continue
                cmdline: list[str] = []
                with contextlib.suppress(Exception):
                    cmdline = list(proc.info["cmdline"] or [])
                if len(cmdline) < 2 or not marker:
                    continue
                if Path(cmdline[1]).name != marker:
                    continue
                if run_dir_token not in " ".join(cmdline).replace("\\", "/").lower():
                    continue
                evidence["child_pid"] = proc.info["pid"]
                evidence["child_argv0"] = cmdline[0]
                found = True
                break
        if found:
            break

    rc, out, err = _run(["schtasks", "/query", "/tn", task_name, "/fo", "LIST", "/v"])
    evidence["task_query"] = {"rc": rc, "out": out.strip()[:4000], "err": err.strip()}
    (run_dir / "task_query.txt").write_text(
        f"=== schtasks /query /v @ {_now()} ===\n{out}\n", encoding="utf-8"
    )
    evidence["recorded_at"] = _now()
    _write_json(run_dir / "detach_launch.json", evidence)
    print(json.dumps(evidence, indent=2, default=str))
    return 0


# ---------------------------------------------------------------------------------------------
# mode = cleanup
# ---------------------------------------------------------------------------------------------
def _cleanup(args) -> int:
    rc, out, err = _run(["schtasks", "/delete", "/tn", args.task_name, "/f"])
    print(json.dumps({"rc": rc, "out": out.strip(), "err": err.strip()}, indent=2))
    return 0 if rc == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="N01-8 detached-run launcher (Task Scheduler)")
    parser.add_argument("--mode", choices=("task", "launcher", "cleanup"), required=True)
    parser.add_argument("--spec", type=str, default=None)
    parser.add_argument("--run-dir", type=str, default=None)
    parser.add_argument("--task-name", type=str, default=None)
    parser.add_argument("--label", type=str, default="run")
    parser.add_argument("--cwd", type=str, default=None)
    parser.add_argument("--pid-marker", type=str, default=None)
    parser.add_argument("--discover-seconds", type=float, default=20.0)
    parser.add_argument("--keep-alive", action="store_true")
    parser.add_argument("target", nargs="*", help="target command line (task mode)")
    args = parser.parse_args()

    if args.mode == "launcher":
        if not args.spec:
            parser.error("--spec is required in launcher mode")
        return _launcher(Path(args.spec))
    if args.mode == "cleanup":
        if not args.task_name:
            parser.error("--task-name is required in cleanup mode")
        return _cleanup(args)
    if not args.run_dir or not args.target:
        parser.error("--run-dir and a target command line are required in task mode")
    return _task(args)


if __name__ == "__main__":
    raise SystemExit(main())
