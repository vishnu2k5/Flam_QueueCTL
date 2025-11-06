# src/queuectl/show.py
import click
from .models import list_jobs

@click.command("show")
@click.option("--state", default=None, help="Filter by job state (e.g. pending, completed, dead).")
@click.option("--limit", default=10, help="Limit number of jobs to display.")
def show(state, limit):
    """
    Show details and output for all jobs (optionally filter by state).
    Example:
      queuectl show               -> shows all recent jobs
      queuectl show --state completed
    """
    jobs = list_jobs(state)
    if not jobs:
        click.echo("No jobs found.")
        return

    # sort by created_at descending so newest first
    jobs = sorted(jobs, key=lambda j: j["created_at"], reverse=True)

    click.echo(f"\nDisplaying up to {limit} job results:\n{'='*50}")
    for job in jobs[:limit]:
        click.echo(f"\n🆔  Job ID: {job['id']}")
        click.echo(f"📜  Command: {job['command']}")
        click.echo(f"📅  Created At: {job['created_at']}")
        click.echo(f"🔁  Attempts: {job['attempts']}/{job['max_retries']}")
        click.echo(f"📊  State: {job['state']}")
        result = job.get("result") or "(no output)"
        click.echo(f"🧾  Result:\n{result}")
        click.echo("-" * 50)
