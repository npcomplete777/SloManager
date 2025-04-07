# features/k8s_inventory.py

import streamlit as st
import pandas as pd
import os
from k8s_data_builder import build_k8s_inventory_csv

def show_k8s_inventory():
    st.header("Build K8s Inventory CSV")

    st.write("""
    This will gather all known K8s clusters, their node lists, and their namespaces (IDs and names),
    and compile them into a single CSV file, with one row per cluster.
    """)

    client = st.session_state["dt_client"]
    config = st.session_state["config"]

    timeframe_col1, timeframe_col2 = st.columns(2)
    with timeframe_col1:
        timeframe_start_inv = st.text_input("Timeframe Start", value="now-24h", help="e.g. 'now-7d'")
    with timeframe_col2:
        timeframe_end_inv = st.text_input("Timeframe End", value="now", help="e.g. 'now'")

    output_filename = st.text_input("Output CSV Filename", value="k8s_inventory.csv")

    if st.button("Build & Download K8s Inventory CSV"):
        try:
            with st.spinner("Building K8s inventory..."):
                df_inv = build_k8s_inventory_csv(
                    client,
                    timeframe_start=timeframe_start_inv,
                    timeframe_end=timeframe_end_inv,
                    output_csv=output_filename
                )
            st.success("K8s inventory built successfully!")
            st.dataframe(df_inv)

            csv_data_inv = df_inv.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv_data_inv,
                file_name=output_filename,
                mime="text/csv"
            )
        except Exception as ex:
            st.error(f"Error building K8s inventory: {ex}")
