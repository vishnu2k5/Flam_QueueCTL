# src/queuectl/worker_core.py
import os
import signal
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .db import get_conn, DB_PATH

# Configuration (can be overridden by env)
BACKOFF_BASE = float(os.getenv("QUEUECTL_BACKOFF_BASE", "2"))  # base for exponential backoff
JOB_TIMEOUT = float(os.getenv("QUEUECTL_JOB_TIMEOUT", "30"))   # seconds; None or 0 = no timeout


# graceful shutdown flag
_SHOULD_STOP = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _on_term(signum, frame):
    global _SHOULD_STOP
    _SHOULD_STOP = True


# register signal handlers
signal.signal(signal.SIGINT, _on_term)
try:
    signal.signal(signal.SIGTERM, _on_term)
except Exception:
    # some environments don't allow SIGTERM binding
    pass


def _claim_one_job(db_path: Optional[str] = None) -> Optional[dict]:
    """
    Atomically claim one pending job by marking it processing and incrementing attempts.
    Returns the job row as dict (after claim) or None if no job available.
    Approach:
      - UPDATE the job whose id = (SELECT id FROM jobs WHERE state='pending' ORDER BY created_at LIMIT 1)
      - If update affected a row, SELECT it back and return.
    """
    p = db_path or DB_PATH
    with get_conn(p) as conn:
        cur = conn.cursor()
        # Use current timestamp
        now = _now_iso()

        # The subquery selects one pending job id (ordered by created_at).
        # The UPDATE is atomic and will affect at most one row.
        cur.execute(
            """
            UPDATE jobs
            SET state='processing',
                attempts = attempts + 1,
                updated_at = ?
            WHERE id = (
                SELECT id FROM jobs WHERE state='pending' ORDER BY created_at LIMIT 1
            )
            """,
            (now,),
        )
        if cur.rowcount == 0:
            return None

        # get that job row (the one we just updated). We select any job in processing
        # with most recent updated_at to be safe.
        cur.execute(
            "SELECT * FROM jobs WHERE state='processing' ORDER BY updated_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        return dict(row) if row else None


def _update_job_state(job_id: str, state: str, db_path: Optional[str] = None, **kwargs):
    """
    Generic helper to update job state and arbitrary columns (result, last_error, attempts).
    kwargs values will be set as-is. updated_at will be set automatically.
    """
    p = db_path or DB_PATH
    with get_conn(p) as conn:
        cur = conn.cursor()
        cols = ["state = ?"]
        vals = [state]
        for k, v in kwargs.items():
            cols.append(f"{k} = ?")
            vals.append(v)
        vals.append(_now_iso())
        sql = f"UPDATE jobs SET {', '.join(cols)}, updated_at = ? WHERE id = ?"
        vals.append(job_id)
        cur.execute(sql, tuple(vals))
        conn.commit()


def _run_command(cmd: str, timeout: Optional[float] = None) -> tuple[int, str, str]:
    """
    Execute command in shell. Returns (exit_code, stdout, stderr).
    Uses subprocess.run with shell=True.
    """
    # Try to run in a shell so a string command like "echo hi" works.
    try:
        completed = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=(timeout if timeout and timeout > 0 else None),
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        return completed.returncode, stdout, stderr
    except subprocess.TimeoutExpired as te:
        return -1, "", f"TimeoutExpired: {te}"
    except Exception as e:
        return -1, "", f"Exception running command: {e}"


def worker_loop(worker_index: int = 0, db_path: Optional[str] = None, backoff_base: Optional[float] = None, job_timeout: Optional[float] = None):
    """
    Main worker loop. Continues until _SHOULD_STOP is True.
    - Claims a job, runs it, updates state/result.
    - On failure and attempts < max_retries, sleeps exponential backoff then requeues.
    - On exhausting retries, marks job 'dead'.
    """
    global _SHOULD_STOP
    backoff_base = float(backoff_base) if backoff_base is not None else BACKOFF_BASE
    job_timeout = float(job_timeout) if job_timeout is not None else JOB_TIMEOUT

    pid = os.getpid()
    print(f"Worker-{worker_index} (PID {pid}) started.")
    # quick loop
    while not _SHOULD_STOP:
        try:
            job = _claim_one_job(db_path=db_path)
        except Exception as e:
            # log and sleep briefly
            print(f"Worker-{worker_index}: claim error: {e}")
            time.sleep(1)
            continue

        if job is None:
            # no pending job — sleep a bit then poll again
            time.sleep(1)
            continue

        job_id = job["id"]
        command = job["command"]
        attempts = int(job.get("attempts", 0))
        max_retries = int(job.get("max_retries", 3))

        print(f"Worker-{worker_index} claimed job {job_id} (attempt {attempts}/{max_retries})")
        # Execute the command
        exit_code, stdout, stderr = _run_command(command, timeout=job_timeout)

        # On success
        if exit_code == 0:
            result_text = (stdout or "").strip()
            try:
                # store result (truncated if huge)
                if len(result_text) > 65500:
                    result_text = result_text[:65500] + "...(truncated)"
                _update_job_state(job_id, "completed", db_path=db_path, result=result_text, last_error=None, attempts=attempts)
            except Exception as e:
                print(f"Worker-{worker_index}: error updating completed state for {job_id}: {e}")
            print(f"Worker-{worker_index} completed job {job_id} (exit 0)")
            continue

        # On failure:
        err_summary = (stderr or "").strip() or f"exit_code={exit_code}"
        print(f"Worker-{worker_index} job {job_id} failed: {err_summary}")

        # If still allowed to retry
        if attempts < max_retries:
            # compute backoff delay using attempts (attempts was incremented when claimed)
            delay = backoff_base ** attempts
            # bound delay to something reasonable (e.g., max 24h)
            max_delay = 24 * 3600
            delay = min(delay, max_delay)
            print(f"Worker-{worker_index} will backoff {delay}s before requeue (attempt {attempts}/{max_retries})")

            # keep job in 'processing' state while sleeping to prevent other workers from picking.
            # This means if worker crashes now, the job will be stuck in 'processing' — acceptable trade-off
            # for simplicity. A more robust design uses a 'locked_until' column.
            slept = 0.0
            while slept < delay and not _SHOULD_STOP:
                to_sleep = min(1.0, delay - slept)
                time.sleep(to_sleep)
                slept += to_sleep

            if _SHOULD_STOP:
                # try to set job back to pending so other workers can pick it up
                try:
                    _update_job_state(job_id, "pending", db_path=db_path)
                except Exception:
                    pass
                break

            # requeue: set state back to pending so other workers can pick it (or this worker)
            try:
                _update_job_state(job_id, "pending", db_path=db_path, last_error=err_summary)
            except Exception as e:
                print(f"Worker-{worker_index}: failed to requeue job {job_id}: {e}")
        else:
            # move to dead (DLQ)
            try:
                _update_job_state(job_id, "dead", db_path=db_path, last_error=err_summary)
            except Exception as e:
                print(f"Worker-{worker_index}: failed to mark job {job_id} dead: {e}")
            print(f"Worker-{worker_index} moved job {job_id} to dead after {attempts} attempts")

    # graceful exit cleanup
    print(f"Worker-{worker_index} (PID {os.getpid()}) shutting down.")
