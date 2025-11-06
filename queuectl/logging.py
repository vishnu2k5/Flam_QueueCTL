# src/queuectl/logging.py
import logging
import sys
from pathlib import Path
from .config import load_config

LOG_PATH = Path(__file__).parent / "queuectl.log"

def setup_logging():
    """Configure global logging (file + console)"""
    cfg = load_config()
    level_name = cfg.get("log_level", "info").upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger("queuectl")
    logger.setLevel(level)

    # Avoid adding multiple handlers if already configured
    if not logger.handlers:
        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # File handler (optional persistent logs)
        fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger

def get_logger(name: str):
    """Return a child logger with module name."""
    setup_logging()
    return logging.getLogger(f"queuectl.{name}")
