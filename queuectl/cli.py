# src/queuectl/cli.py
import click
from .enqueue import enqueue
from .list_jobs import list_jobs_cmd
from .workers import worker_group
from .status import status
from .dlq import dlq_group
from .config import config_group
from .logging import get_logger
@click.group()
def cli():
    """QueueCTL — CLI for job queue (enqueue, workers, status, dlq, ...)"""
    pass

# register commands
cli.add_command(enqueue)
cli.add_command(list_jobs_cmd)
cli.add_command(worker_group)
cli.add_command(status)
cli.add_command(dlq_group)
cli.add_command(config_group)
logger = get_logger("worker")
logger.info("Worker started successfully")
logger.error("Job failed with exit code 1")
# future: import and add other commands like worker group, status, dlq, config, etc.
