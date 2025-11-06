# src/queuectl/dlq.py
import json
from pathlib import Path
from typing import List

import click

from .db import get_conn, DB_PATH
from .models import now_iso

# optional rich UI
try:
    from rich.console import Console
    from rich.table import Table

    _HAS_RICH = True
    _console = Console()
except Exception:
    _HAS_RICH = False
    _console = None


def _fetch_dead_jobs(db_path: Path | str | None = None) -> List[dict]:
    p = db_path or DB_PATH
    with get_conn(p) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM jobs WHERE state='dead' ORDER BY updated_at DESC")
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def _retry_job_in_db(job_id: str, db_path: Path | str | None = None) -> bool:
    """
    Reset a dead job to pending and reset attempts/last_error.
    Returns True if a row was updated, False if job not found or not dead.
    """
    p = db_path or DB_PATH
    with get_conn(p) as conn:
        cur = conn.cursor()
        # Only update if state is dead (safety)
        cur.execute(
            "UPDATE jobs SET state='pending', attempts=0, last_error=NULL, updated_at=? WHERE id=? AND state='dead'",
            (now_iso(), job_id),
        )
        changed = cur.rowcount
        conn.commit()
        return bool(changed)


@click.group("dlq")
def dlq_group():
    """Dead Letter Queue (view & retry permanently failed jobs)."""
    pass


@dlq_group.command("list")
def dlq_list():
    """List jobs in the Dead Letter Queue (state='dead')."""
    rows = _fetch_dead_jobs()
    if not rows:
        click.echo("No dead jobs found.")
        return

    if _HAS_RICH:
        table = Table(title="QueueCTL Dead Letter Queue")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("COMMAND", style="green")
        table.add_column("ATTEMPTS", justify="right")
        table.add_column("MAX_RETRIES", justify="right")
        table.add_column("LAST_ERROR", style="red")
        table.add_column("UPDATED_AT", style="dim")
        for r in rows:
            table.add_row(
                r.get("id", ""),
                (r.get("command") or "")[:140],
                str(r.get("attempts", "")),
                str(r.get("max_retries", "")),
                r.get("last_error") or "",
                r.get("updated_at") or "",
            )
        _console.print(table)
        return

    # fallback JSON/text
    click.echo(json.dumps(rows, indent=2))


@dlq_group.command("retry")
@click.argument("job_id", required=False)
@click.option("--all", "retry_all", is_flag=True, help="Retry all jobs in the DLQ.")
def dlq_retry(job_id: str, retry_all: bool):
    """
    Retry a job from the DLQ:
      queuectl dlq retry <job_id>
    Or retry everything:
      queuectl dlq retry --all
    """
    if not retry_all and not job_id:
        click.echo("Specify a job_id or use --all to retry everything.")
        raise SystemExit(1)

    if retry_all:
        rows = _fetch_dead_jobs()
        if not rows:
            click.echo("No dead jobs to retry.")
            return
        cnt = 0
        for r in rows:
            ok = _retry_job_in_db(r["id"])
            if ok:
                cnt += 1
        click.echo(f"Retried {cnt} job(s) from DLQ.")
        return

    # single job retry
    ok = _retry_job_in_db(job_id)
    if ok:
        click.echo(f"Job {job_id} moved back to pending (retries reset).")
    else:
        click.echo(f"Job {job_id} not found in DLQ (or not in 'dead' state).")
