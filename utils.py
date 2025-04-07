# utils.py

import yaml
import re
from datetime import datetime, timedelta

def parse_time(time_str: str) -> datetime:
    """
    Converts a shorthand time expression (e.g., "now", "now-7d", "now-60m") into a UTC datetime.
    """
    now = datetime.utcnow()
    if time_str.strip() == "now":
        return now

    # Match days
    days_match = re.match(r"now-(\d+)d", time_str.strip())
    if days_match:
        days = int(days_match.group(1))
        return now - timedelta(days=days)

    # Match minutes
    minutes_match = re.match(r"now-(\d+)m", time_str.strip())
    if minutes_match:
        minutes = int(minutes_match.group(1))
        return now - timedelta(minutes=minutes)

    # Match hours
    hours_match = re.match(r"now-(\d+)h", time_str.strip())
    if hours_match:
        hours = int(hours_match.group(1))
        return now - timedelta(hours=hours)

    raise ValueError(f"Unrecognized time format: {time_str}")

def iso8601(dt: datetime) -> str:
    """Return an ISO8601 string in UTC with a trailing Z."""
    return dt.isoformat() + "Z"

def load_default_config() -> dict:
    """
    Load credentials from config.yaml if present.
    If not found or if there's an error, return a minimal default.
    """
    try:
        with open("config.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Could not load config.yaml: {e}")
        return {
            "base_url": "",
            "platform_token": "",
            "settings": {
                "output_dir": "output",
                "output_format": "csv"
            }
        }

def load_queries() -> dict:
    """
    Load queries from queries.yaml if available.
    """
    try:
        with open("queries.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Could not load queries.yaml: {e}")
        return {}
