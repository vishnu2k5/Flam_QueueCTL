# src/queuectl/list_jobs.py
import json
import click
from typing import Optional

# try to use rich for pretty output, otherwise fallback to JSON
try:
    from rich.console import Console
    from rich.table import Table

    _HAS_RICH = True
    _console = Console()
except Exception:
    _HAS_RICH = False
    _console = None

from .models import list_jobs


@click.command("list")
@click.option(
    "--state",
    default=None,
    help="Filter by state (pending, processing, completed, failed, dead).",
)
@click.option("--limit", default=None, type=int, help="Limit number of rows shown.")
@click.option(
    "--pretty/--no-pretty",
    default=True,
    help="Use pretty table output (requires 'rich'). Set --no-pretty to get JSON.",
)
def list_jobs_cmd(state: Optional[str], limit: Optional[int], pretty: bool):
    """
    List jobs in the queue. Pass --state to filter by state, e.g. --state pending.
    """
    # fetch rows
    rows = list_jobs(state)

    if limit:
        rows = rows[:limit]

    # If user requested pretty output but rich not available -> warn and fallback
    if pretty and not _HAS_RICH:
        click.echo(
            "Note: 'rich' not available. Install with `poetry add rich` to enable pretty tables."
        )
        pretty = False

    if pretty:
        table = Table(title="QueueCTL Jobs")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("STATE", style="magenta")
        table.add_column("ATTEMPTS", justify="right")
        table.add_column("MAX_RETRIES", justify="right")
        table.add_column("COMMAND", style="green")
        table.add_column("CREATED_AT", style="dim")

        for r in rows:
            table.add_row(
                r.get("id", ""),
                r.get("state", ""),
                str(r.get("attempts", "")),
                str(r.get("max_retries", "")),
                (r.get("command") or "")[:120],  # truncate long commands for table
                r.get("created_at", ""),
            )
        _console.print(table)
        return

    # fallback: JSON output
    click.echo(json.dumps(rows, indent=2))
