# 🔥 Flam_QueueCTL

A CLI-based background job queue system built with **Python + Click + SQLite**.  
Flam_QueueCTL manages background jobs, worker processes, automatic retries (with exponential backoff), and a Dead Letter Queue (DLQ).

---

## 🚀 Overview

Flam_QueueCTL allows you to:

- 🧾 Enqueue shell commands as background jobs  
- ⚙️ Run multiple worker processes in parallel  
- 🔁 Retry failed jobs automatically with exponential backoff  
- ☠️ Move permanently failed jobs to a Dead Letter Queue (DLQ)  
- 📊 Monitor job states & worker status via CLI  
- ⚡ Persist all jobs in a SQLite database  
- 🧠 Configure global settings (max retries, backoff delay, log level)

The system is implemented entirely as a **CLI application**, built using the [Click](https://click.palletsprojects.com/) framework and managed with [Poetry](https://python-poetry.org/).

---

## 🧩 Architecture & Design

- **Database**: `queuectl.db` — stores all jobs and states.  
- **Worker**: executes shell commands, retries on failure, applies exponential backoff, and updates state.  
- **DLQ**: handles permanently failed jobs (`state='dead'`).  
- **PID File**: tracks active worker PIDs in `~/.queuectl_workers.json`.  
- **Config File**: stores global settings in `.queuectl_config.json`.

---

## ⚙️ Setup Instructions

### 🧱 Requirements
- Python **3.11+**
- [Poetry](https://python-poetry.org/)

### 📦 Installation
```bash
git clone https://github.com/vishnu2k5/Flam_QueueCTL.git
cd Flam_QueueCTL
poetry install
🧩 Run Commands

Example usage inside the Poetry environment:

poetry run queuectl enqueue --command "echo Hello QueueCTL"
poetry run queuectl worker start --count 2
poetry run queuectl status

💻 CLI Commands
Command	Example	Description
Enqueue	queuectl enqueue --command "echo Hello"	Add a job to the queue
Workers	queuectl worker start --count 2	Start one or more workers
	queuectl worker stop	Stop all running workers
Status	queuectl status	Show job summary and worker PIDs
List Jobs	queuectl list --state completed	List jobs filtered by state
Show Output	queuectl show	Display job results and outputs
DLQ	queuectl dlq list	Show permanently failed jobs
	queuectl dlq retry <job_id>	Re-enqueue one DLQ job
	queuectl dlq retry --all	Retry all DLQ jobs
Config	queuectl config show	Display current config
	queuectl config set max_retries 5	Update configuration values
🔁 Job Lifecycle
State	Description
pending	Waiting to be picked up by a worker
processing	Currently executing
completed	Successfully executed
failed	Failed but retryable
dead	Permanently failed, moved to DLQ
Exponential Backoff

For retries, QueueCTL uses the formula:

delay = base ^ attempts


Example (base = 2): 1s → 2s → 4s → 8s

⚙️ Configuration System

Global defaults are stored in .queuectl_config.json.

Example file:

{
    "max_retries": 3,
    "backoff_seconds": 2,
    "log_level": "info"
}


Change settings using:

queuectl config set max_retries 5
queuectl config set backoff_seconds 3
queuectl config show

☠️ Dead Letter Queue (DLQ)

Jobs that fail all retries are moved to the DLQ.

List all:

queuectl dlq list


Retry one:

queuectl dlq retry <job_id>


Retry all:

queuectl dlq retry --all

🧾 Logging (Optional)

QueueCTL supports optional logging to a file queuectl.log.

Example entry:

[2025-11-06 12:45:10] [INFO] [queuectl.worker] Worker PID 23456 started
[2025-11-06 12:45:12] [ERROR] [queuectl.worker] Job 123 failed (exit code 1)


Control log level via:

queuectl config set log_level debug

🧪 Testing Scenarios

✅ Basic success — Enqueue a job (echo "Hi") and see it complete.

❌ Failure test — Enqueue a failing job (exit 1) and verify retries & DLQ.

🔁 Multi-worker test — Run multiple workers and confirm no duplicate job processing.

🧱 Persistence — Stop workers and restart; verify jobs remain in DB.

⚙️ Config — Update max_retries in config and test new behavior.

🧠 Key Design Decisions

SQLite used for local persistence (simple, file-based).

Exponential backoff prevents retry storms.

Worker state tracked in JSON for cross-process visibility.

Modular code structure: enqueue, worker_core, status, dlq, config, logging.

Click CLI groups commands cleanly for scalability.

Configurable defaults allow environment-specific tuning.

📁 Project Structure
queuectl/
├── cli.py                # CLI entrypoint (Click)
├── enqueue.py            # Add jobs to queue
├── worker_core.py        # Worker loop & retry logic
├── status.py             # Show system & worker status
├── list_jobs.py          # List all jobs
├── dlq.py                # Dead Letter Queue logic
├── config.py             # Config management
├── db.py                 # SQLite persistence
├── models.py             # Job model and helpers
└── logging.py            # Central logging (optional)

⚖️ Assumptions & Trade-offs

Designed for local use (SQLite not distributed).

Backoff = exponential by default; configurable via config.

Jobs executed with shell=True → avoid unsafe inputs.

Simple worker locking (safe for small scale).

Stuck “processing” jobs can be manually reset if needed.


🙌 Acknowledgements

Click
 — CLI framework

Rich
 — pretty console tables

psutil
 — cross-platform process checking

Poetry
 — dependency management


