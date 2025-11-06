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

