# src/queuectl/enqueue.py
import json
import click
from .models import Job, gen_id, insert_job
from .db import init_db
from .config import load_config 

@click.command("enqueue")
@click.argument("payload", required=False)
@click.option("--id", "job_id", default=None, help="Job id (optional UUID).")
@click.option("--command", "cmd", default=None, help="Command to execute (shell).")
@click.option("--max-retries", default=None, type=int, help="Max retries for the job.")
@click.option("--db-path", default=None, help="Optional path to sqlite DB.")
def enqueue(payload, job_id, cmd, max_retries, db_path):
    """
    Enqueue a job. Provide either a JSON payload or use flags.

    JSON example:
      queuectl enqueue '{"command":"echo hello","max_retries":3}'
       queuectl enqueue --command "echo Hello from queuectl" --max-retries 2
    """
    # ensure DB exists
    init_db(db_path)

    data = {}
    if payload:
        try:
            data = json.loads(payload)
            if not isinstance(data, dict):
                click.echo("Payload must be a JSON object.")
                raise SystemExit(1)
        except json.JSONDecodeError as e:
            click.echo(f"Invalid JSON payload: {e}")
            raise SystemExit(1)

    # flags override JSON if provided
    cmd = cmd or data.get("command")
    if not cmd:
        click.echo("Missing 'command'. Use --command or provide JSON with command.")
        raise SystemExit(1)

    job_id = job_id or data.get("id") or gen_id()
    # mr = max_retries if max_retries is not None else data.get("max_retries", 3)
    cfg = load_config()
    if max_retries is not None:
        mr=max_retries
    elif "max_retries" in data:
        mr=int(data["max_retries"])
    else:
        mr = cfg.get("max_retries", 3)
    

    job = Job(id=job_id, command=cmd, max_retries=int(mr))
    insert_job(job, db_path)
    click.echo(f"Enqueued job {job_id}")
