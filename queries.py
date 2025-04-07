import yaml
import os

QUERIES_PATH = os.path.join(os.path.dirname(__file__), "queries.yaml")

def load_queries():
    """
    Loads and returns the contents of queries.yaml as a Python dict.
    """
    with open(QUERIES_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# We load queries on import so that they're readily available throughout the app.
queries = load_queries()
