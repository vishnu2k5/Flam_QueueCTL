# src/queuectl/db.py
import sqlite3
from pathlib import Path
from contextlib import contextmanager

# default DB path (user's home)
DB_PATH = Path(__file__).parent / "queuectl.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    command TEXT NOT NULL,
    state TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_error TEXT,
    result TEXT
);
"""

def init_db(path: str | Path | None = None):
    """Initialize DB file and schema. Optionally pass custom path."""
    p = Path(path) if path else DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    return p

@contextmanager
def get_conn(path: str | Path | None = None):
    """Yield sqlite3.Connection with row access by name."""
    p = Path(path) if path else DB_PATH
    conn = sqlite3.connect(p, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
