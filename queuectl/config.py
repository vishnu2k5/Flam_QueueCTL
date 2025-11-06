# src/queuectl/config.py
import json
from pathlib import Path
import click

CONFIG_PATH = Path(__file__).parent / ".queuectl_config.json"
DEFAULT_CONFIG = {
    "max_retries": 3,
    "backoff_seconds": 2,
    "log_level": "info",
}

def load_config() -> dict:
    """Load config from JSON file or create with defaults."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            click.echo("⚠️  Config file corrupted, using defaults.")
            return DEFAULT_CONFIG.copy()
    else:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

def save_config(cfg: dict):
    """Save config to JSON file."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

@click.group("config")
def config_group():
    """Manage QueueCTL configuration (retry, backoff, etc.)."""
    pass

@config_group.command("show")
def show_config():
    """Display the current configuration."""
    cfg = load_config()
    click.echo(json.dumps(cfg, indent=4))

@config_group.command("get")
@click.argument("key")
def get_config(key):
    """Get a specific config value by key."""
    cfg = load_config()
    if key not in cfg:
        click.echo(f"❌ Key '{key}' not found in configuration.")
        return
    click.echo(f"{key} = {cfg[key]}")

@config_group.command("set")
@click.argument("key")
@click.argument("value")
def set_config(key, value):
    """Set a configuration key to a new value.
    Example:
      queuectl config set max_retries 5
    """
    cfg = load_config()
    # try to cast numeric values
    try:
        if value.isdigit():
            value = int(value)
        elif value.lower() in ("true", "false"):
            value = value.lower() == "true"
    except Exception:
        pass

    cfg[key] = value
    save_config(cfg)
    click.echo(f"✅ Updated {key} = {value}")
