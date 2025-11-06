# src/queuectl/workers.py  (replace existing start/stop implementations)
import json
import os
import signal
import sys
from datetime import datetime, timezone
from multiprocessing import Process
from pathlib import Path
from time import sleep, time
import click

from .worker_core import worker_loop  # your real worker function
WORKER_FILE = Path(__file__).parent / ".queuectl_workers.json"



def _write_workers_file_from_pids(pids):
    data = [{"pid": int(pid), "started_at": datetime.now(timezone.utc).isoformat()} for pid in pids]
    tmp = WORKER_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(WORKER_FILE)


def _read_pids_file():
    if not WORKER_FILE.exists():
        return []
    try:
        data = json.loads(WORKER_FILE.read_text(encoding="utf-8"))
        return [d.get("pid") for d in data if "pid" in d]
    except Exception:
        return []


@click.group("worker")
def worker_group():
    pass


@worker_group.command("start")
@click.option("--count", default=1, show_default=True, help="Number of workers to start.")
def start_workers(count):
    """Start one or more worker processes and register their PIDs."""
    procs = []
    pids = []
    for i in range(count):
        p = Process(target=worker_loop, args=(i,), daemon=False)
        p.start()
        procs.append(p)
        pids.append(p.pid)
        click.echo(f"Started worker-{i} (PID {p.pid})")

    # write pid file for status checks
    _write_workers_file_from_pids(pids)
    click.echo(f"{count} worker(s) started and registered in {WORKER_FILE}")

    def _terminate_children():
        # send SIGTERM to all children processes
        for p in procs:
            try:
                if p.is_alive():
                    os.kill(p.pid, signal.SIGTERM)
            except Exception:
                pass

    try:
        # Keep the parent alive; wait for children.
        while True:
            # if all children finished, break and cleanup
            alive = [p.is_alive() for p in procs]
            if not any(alive):
                click.echo("All worker processes have exited.")
                break
            sleep(1)
    except KeyboardInterrupt:
        click.echo("KeyboardInterrupt received — stopping workers gracefully...")
        _terminate_children()
        # wait up to N seconds for children to exit
        deadline = time() + 10.0  # wait up to 10s
        while time() < deadline and any(p.is_alive() for p in procs):
            sleep(0.5)
        # final attempt: force terminate if still alive
        for p in procs:
            try:
                if p.is_alive():
                    os.kill(p.pid, signal.SIGKILL)
            except Exception:
                pass
        click.echo("Workers signalled to stop; cleaning up PID file.")

    # After children exited (or we forced them), remove the worker file.
    try:
        if WORKER_FILE.exists():
            WORKER_FILE.unlink(missing_ok=True)
            click.echo(f"Removed PID file {WORKER_FILE}")
    except Exception:
        click.echo(f"Could not remove PID file {WORKER_FILE}; please delete manually if needed.")


@worker_group.command("stop")
def stop_workers():
    """Stop running workers (reads PIDs from pid file)."""
    pids = _read_pids_file()
    if not pids:
        click.echo("No active workers found.")
        return

    click.echo(f"Stopping {len(pids)} worker(s)...")
    for pid in pids:
        try:
            os.kill(int(pid), signal.SIGTERM)
            click.echo(f"Sent SIGTERM to worker PID {pid}")
        except ProcessLookupError:
            click.echo(f"PID {pid} not found.")
        except Exception as e:
            click.echo(f"Could not stop PID {pid}: {e}")

    # allow a short grace period then remove pid file
    sleep(1.5)
    try:
        if WORKER_FILE.exists():
            WORKER_FILE.unlink(missing_ok=True)
            click.echo(f"Removed PID file {WORKER_FILE}")
    except Exception:
        click.echo(f"Unable to remove {WORKER_FILE}; please remove manually.")
