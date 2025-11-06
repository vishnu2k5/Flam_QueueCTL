# src/queuectl/models.py
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import uuid
from .db import get_conn

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def gen_id() -> str:
    return str(uuid.uuid4())

@dataclass
class Job:
    id: str
    command: str
    state: str = "pending"
    attempts: int = 0
    max_retries: int = 3
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_error: Optional[str] = None
    result: Optional[str] = None

    def __post_init__(self):
        ts = now_iso()
        if self.created_at is None:
            self.created_at = ts
        if self.updated_at is None:
            self.updated_at = ts

    def to_tuple(self):
        return (
            self.id,
            self.command,
            self.state,
            self.attempts,
            self.max_retries,
            self.created_at,
            self.updated_at,
            self.last_error,
            self.result,
        )

# CRUD helpers
def insert_job(job: Job, db_path: str | None = None) -> None:
    with get_conn(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO jobs (id,command,state,attempts,max_retries,created_at,updated_at,last_error,result) VALUES (?,?,?,?,?,?,?,?,?)",
            job.to_tuple(),
        )
        conn.commit()

def list_jobs(state: str | None = None, db_path: str | None = None):
    with get_conn(db_path) as conn:
        cur = conn.cursor()
        if state:
            cur.execute("SELECT * FROM jobs WHERE state=? ORDER BY created_at", (state,))
        else:
            cur.execute("SELECT * FROM jobs ORDER BY created_at")
        rows = cur.fetchall()
        return [dict(r) for r in rows]

def get_job(job_id: str, db_path: str | None = None):
    with get_conn(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
        r = cur.fetchone()
        return dict(r) if r else None
