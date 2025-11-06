# src/queuectl/status.py
import os
import json
import platform
from datetime import datetime
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table
from rich import box

from .db import get_conn, DB_PATH

console = Console()

# Worker file location (same one used by worker.py)
WORKER_FILE = Path(__file__).parent / ".queuectl_workers.json"

# Try to use psutil if available
try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


def _is_process_alive(pid: int) -> bool:
    """Cross-platform check if a process is alive."""
    try:
        pid = int(pid)
    except Exception:
        return False

    # 1️⃣ Use psutil if available (most reliable)
    if _HAS_PSUTIL:
        try:
            return psutil.pid_exists(pid)
        except Exception:
            pass

    # 2️⃣ Fallback for Unix
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False  # No such process
    except PermissionError:
        return True   # Process exists, but we can't signal it
    except OSError:
        pass
    else:
        return True

    # 3️⃣ Fallback for Windows via ctypes
    if platform.system().lower().startswith("windows"):
        try:
            import ctypes
            from ctypes import wintypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            OpenProcess = kernel32.OpenProcess
            OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
            OpenProcess.restype = wintypes.HANDLE
            CloseHandle = kernel32.CloseHandle

            handle = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            CloseHandle(handle)
            return True
        except Exception:
            return False

    return False


def _read_worker_file() -> list:
    """Read worker PID file and return list of workers."""
    if not WORKER_FILE.exists():
        return []
    try:
        with open(WORKER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        return []


@click.command("status")
def status():
    """Show summary of job states and active workers."""
    with get_conn(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT state, COUNT(*) as cnt FROM jobs GROUP BY state")
        rows = cur.fetchall()

    state_counts = {r["state"]: r["cnt"] for r in rows}
    total_jobs = sum(state_counts.values())

    table = Table(title="QueueCTL System Status", box=box.SIMPLE_HEAVY)
    table.add_column("Category", style="bold magenta")
    table.add_column("Details", style="cyan")

    # Job summary
    job_summary = ", ".join(f"{k}={v}" for k, v in state_counts.items()) or "No jobs"
    table.add_row(f"Jobs ({total_jobs})", job_summary)

    # Worker summary
    workers = _read_worker_file()
    if not workers:
        table.add_row("Workers", "No registered workers found.")
    else:
        for w in workers:
            pid = w.get("pid")
            started_at = w.get("started_at", "")
            alive = _is_process_alive(pid)
            emoji = "🟢" if alive else "🔴"
            state = "running" if alive else "stopped"
            table.add_row(f"Worker PID {pid}", f"{emoji} {state} (started {started_at})")

    console.print(table)
