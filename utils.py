# utils.py

import os
import yaml
import re
from datetime import datetime, timedelta

def parse_time(time_str: str) -> datetime:
    """
    Converts a shorthand time expression (e.g., "now", "now-7d", "now-60m") into a UTC datetime.
    """
    now = datetime.utcnow()
    time_str = time_str.strip()
    if time_str == "now":
        return now

    # Match days
    days_match = re.match(r"now-(\d+)d", time_str)
    if days_match:
        days = int(days_match.group(1))
        return now - timedelta(days=days)

    # Match minutes
    minutes_match = re.match(r"now-(\d+)m", time_str)
    if minutes_match:
        minutes = int(minutes_match.group(1))
        return now - timedelta(minutes=minutes)

    # Match hours
    hours_match = re.match(r"now-(\d+)h", time_str)
    if hours_match:
        hours = int(hours_match.group(1))
        return now - timedelta(hours=hours)

    raise ValueError(f"Unrecognized time format: {time_str}")

def iso8601(dt: datetime) -> str:
    """Return an ISO8601 string in UTC with a trailing Z."""
    return dt.isoformat() + "Z"

def load_default_config() -> dict:
    """
    Load credentials from config.yaml.
    
    This function determines the absolute path of config.yaml using the location of this file.
    It will work regardless of the working directory, which is especially useful on Windows.
    """
    try:
        # Get the absolute path of the directory where this file is located.
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Assume config.yaml is in the same directory as this file.
        config_path = os.path.join(base_dir, "config.yaml")
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Could not load config.yaml at {config_path if 'config_path' in locals() else 'unknown location'}: {e}")
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
    Load queries from queries.yaml.
    
    Determines the absolute path similarly to load_default_config.
    """
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        queries_path = os.path.join(base_dir, "queries.yaml")
        with open(queries_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Could not load queries.yaml at {queries_path if 'queries_path' in locals() else 'unknown location'}: {e}")
        return {}
