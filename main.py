import streamlit as st
import pandas as pd
import yaml
import logging
import os
import re
import json
import csv
from io import StringIO
from datetime import datetime, timedelta

# Import your own modules
from platform_client import DynatracePlatformClient
from ui_components import render_logo
from utils import load_default_config
from features.csv_manager import show_csv_manager
from features.slo_list_delete import show_slo_list_delete
from features.slo_create import show_slo_create
from features.slo_update import show_slo_update
from features.dql_queries import show_dql_queries
from features.k8s_inventory import show_k8s_inventory

# Configure logging (optional)
logging.basicConfig(level=logging.INFO)

def main():
    # Set page config
    st.set_page_config(page_title="Dynatrace Platform Manager", layout="wide")

    # Render your logo on the sidebar (if applicable)
    render_logo()
    st.title("Dynatrace Platform Manager")

    # 1) Load config.yaml for credentials if not in session
    if "config" not in st.session_state:
        st.session_state["config"] = load_default_config()

    config = st.session_state["config"]

    # --- SIDEBAR CONFIG ---
    with st.sidebar:
        st.header("Dynatrace Configuration")

        base_url = st.text_input(
            "Base URL",
            value=config.get("base_url", ""),
            placeholder="https://your-environment.apps.dynatrace.com"
        )

        platform_token = st.text_input(
            "Platform Token",
            value=config.get("platform_token", ""),
            type="password",
            placeholder="Enter your platform token"
        )

        if base_url and platform_token:
            st.session_state["config"]["base_url"] = base_url
            st.session_state["config"]["platform_token"] = platform_token

            if st.button("Save Configuration"):
                try:
                    with open("config.yaml", "w") as f:
                        yaml.dump(st.session_state["config"], f)
                    st.success("Configuration saved to config.yaml")
                except Exception as e:
                    st.error(f"Error saving configuration: {e}")

    # --- CHECK MINIMUM CONFIG ---
    if not config.get("base_url") or not config.get("platform_token"):
        st.warning("Please enter the Dynatrace base URL and platform token in the sidebar to continue.")
        return

    # 2) Initialize the Platform client once, store in session state
    if "dt_client" not in st.session_state:
        st.session_state["dt_client"] = DynatracePlatformClient(
            base_url=config["base_url"],
            platform_token=config["platform_token"]
        )

    # 3) Dictionary of default CSV file paths (for the CSV Manager tab)
    if "csv_paths" not in st.session_state:
        st.session_state["csv_paths"] = {
            "Services (ZURICH_APPS_SERVICES_WITH_TAGS)": "ZURICH_APPS_SERVICES_WITH_TAGS.csv",
            "Hosts (ZURICH_HOSTS_WITH_TAGS)": "ZURICH_HOSTS_WITH_TAGS.csv",
            "K8s Clusters (ZURICH_K8s_CLUSTERS)": "ZURICH_K8s_CLUSTERS.csv",
            "K8s Namespaces (ZURICH_K8s_NAMESPACES_BY_CLUSTER)": "ZURICH_K8s_NAMESPACES_BY_CLUSTER.csv"
        }

    # 4) Create the six tabs
    tab_csv_manager, tab_list_delete, tab_create, tab_update, tab_dql, tab_k8s_inventory = st.tabs([
        "CSV Manager",
        "List & Delete SLOs",
        "Create SLOs",
        "Update SLOs",
        "Run DQL Queries",
        "K8s Inventory Builder"
    ])

    # Delegate each tab to its own function in features/
    with tab_csv_manager:
        show_csv_manager()

    with tab_list_delete:
        show_slo_list_delete()

    with tab_create:
        show_slo_create()

    with tab_update:
        show_slo_update()

    with tab_dql:
        show_dql_queries()

    with tab_k8s_inventory:
        show_k8s_inventory()


if __name__ == "__main__":
    main()
