# utils.py

import pandas as pd
import csv
import json
import ast
from datetime import datetime, timedelta
import streamlit as st
import yaml

def load_default_config():
    """Loads the default configuration from config.yaml."""
    try:
        with open("config.yaml", "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        st.error("Fatal: config.yaml not found.")
        return {} # Return empty dict to avoid further errors
    except Exception as e:
        st.error(f"Error loading config.yaml: {e}")
        return {}

def parse_time(time_str: str) -> datetime:
    """Parses a relative time string like 'now-7d' into a datetime object."""
    now = datetime.utcnow()
    time_str = time_str.lower().strip()
    if time_str == "now":
        return now
    if time_str.startswith("now-"):
        try:
            part = time_str.replace("now-", "")
            value_str = part[:-1]
            unit = part[-1]
            value = int(value_str)

            if unit == 'd':
                return now - timedelta(days=value)
            elif unit == 'h':
                return now - timedelta(hours=value)
            elif unit == 'm':
                return now - timedelta(minutes=value)
            else:
                raise ValueError(f"Unknown time unit: {unit}")
        except Exception as e:
            raise ValueError(f"Could not parse relative time '{time_str}': {e}")
    # Fallback for absolute time strings
    return datetime.fromisoformat(time_str.replace("Z", "+00:00"))

def iso8601(dt: datetime) -> str:
    """Converts a datetime object to an ISO 8601 string suitable for APIs."""
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

def load_all_slos(client):
    """
    Paginates through all SLOs from the API and returns them as a single list.
    """
    all_slos = []
    page_key = None
    while True:
        response_json = client.list_slos(page_size=200, page_key=page_key)
        items = response_json.get("slos", [])
        all_slos.extend(items)
        page_key = response_json.get("nextPageKey")
        if not page_key:
            break
    return all_slos

EXPECTED_HEADERS = ["app", "services", "env", "criticality", "bu"]

def robust_read_csv(path: str) -> pd.DataFrame:
    """
    Read the template CSV and repair any row whose list field (services / hosts /
    namespace) was split by stray commas. Returns a proper 5-column DataFrame.
    """
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        rdr = csv.reader(fh)
        try:
            headers = next(rdr)
        except StopIteration:
            raise ValueError("CSV is empty")
        # For K8s files, headers are different. This function is specific for the 5-column app/service files.
        # A more advanced version could take expected_headers as an argument.
        # For now, we will bypass the check if it's not the standard 5 headers.
        if [h.strip() for h in headers] != EXPECTED_HEADERS:
            st.warning(f"CSV header does not match the expected standard: {','.join(EXPECTED_HEADERS)}. Reading anyway.")
            # Reset reader and read all data including the header row
            fh.seek(0)
            all_data = list(csv.reader(fh))
            headers = [h.strip() for h in all_data[0]]
            raw_rows = all_data[1:]
        else:
            raw_rows = rdr

        for raw in raw_rows:
            if not raw:
                continue
            # If commas inside the list shattered a 5-column row, stitch it:
            if len(headers) == 5 and len(raw) > 5:
                fixed = [raw[0]]          # app
                i = 1
                list_piece = raw[i]
                while i + 1 < len(raw) and "]" not in list_piece:
                    i += 1
                    list_piece += "," + raw[i]
                fixed.append(list_piece)
                fixed.extend(raw[i + 1 : i + 5])  # env, criticality, bu
                raw = fixed

            rows.append(raw)

    # Handle case where rows have different lengths than headers (for non-5-column files)
    # This makes the function more robust for K8s files too.
    df = pd.DataFrame(rows)
    if df.shape[1] == len(headers):
        df.columns = headers
    else:
        st.error("Column/data mismatch in CSV. Cannot reliably process.")
        return pd.DataFrame()

    return df


def parse_list_field(raw) -> list[str]:
    """
    Convert a CSV cell into a list. Accepts multiple formats.
    """
    raw = str(raw).strip()
    if not raw or raw.lower() == 'nan':
        return []
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1].replace('""', '"')
    # try json
    for candidate in (raw, raw.replace("'", '"')):
        try:
            val = json.loads(candidate)
            if isinstance(val, list):
                return [str(x).strip() for x in val]
            return [str(val).strip()]
        except (json.JSONDecodeError, TypeError):
            pass
    # try ast
    try:
        val = ast.literal_eval(raw)
        if isinstance(val, list):
            return [str(x).strip() for x in val]
        return [str(val).strip()]
    except (ValueError, SyntaxError):
        pass
    # plain comma split
    if "," in raw:
        return [x.strip().strip('"').strip("'") for x in raw.split(",") if x.strip()]
    return [raw.strip().strip('"').strip("'")]