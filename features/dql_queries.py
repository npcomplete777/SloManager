# features/dql_queries.py

import streamlit as st
import pandas as pd
import json
import csv
from io import StringIO
import traceback

from utils import parse_time, iso8601
from queries import load_queries

def show_dql_queries():
    st.header("Run Dynatrace Query Language (DQL) Queries")

    client = st.session_state["dt_client"]
    config = st.session_state["config"]

    # Load saved queries from queries.yaml
    saved_queries = load_queries()

    query_option_col1, query_option_col2 = st.columns([1, 2])
    with query_option_col1:
        query_source = st.radio(
            "Query Source",
            options=["Manual Input", "Saved Queries"],
            index=0,
            key="query_source"
        )

    if query_source == "Manual Input":
        dql_query_text = st.text_area(
            "Enter your DQL query:",
            height=200,
            placeholder="Example: fetch bizevents | limit 100",
            key="dql_query_input"
        )
        default_timeframe_start = "now-1h"
        default_timeframe_end = "now"
        default_max_results = 1000
    else:
        if not saved_queries:
            st.warning("No saved queries found in queries.yaml.")
            dql_query_text = st.text_area(
                "Enter your DQL query:",
                height=200,
                placeholder="Example: fetch bizevents | limit 100",
                key="dql_query_input_fallback"
            )
            default_timeframe_start = "now-1h"
            default_timeframe_end = "now"
            default_max_results = 1000
        else:
            selected_query_name = st.selectbox(
                "Select a saved query",
                options=list(saved_queries.keys()),
                key="selected_saved_query"
            )
            selected_query = saved_queries.get(selected_query_name, {})
            dql_query_text = selected_query.get("query", "")

            # Show in text area for possible editing
            dql_query_text = st.text_area(
                "Query (editable):",
                value=dql_query_text,
                height=200,
                key="dql_query_from_saved"
            )

            default_timeframe_start = selected_query.get("timeframe_start", "now-1h")
            default_timeframe_end = selected_query.get("timeframe_end", "now")
            default_max_results = selected_query.get("maxResultRecords", 1000)

    st.subheader("Query Parameters")
    col1, col2, col3 = st.columns(3)
    with col1:
        timeframe_start = st.text_input(
            "Timeframe Start",
            value=default_timeframe_start,
            help="Supported formats: 'now', 'now-Nd', 'now-Nm', 'now-Nh'",
            key="dql_timeframe_start"
        )
    with col2:
        timeframe_end = st.text_input(
            "Timeframe End",
            value=default_timeframe_end,
            help="Supported formats: 'now', 'now-Nd', 'now-Nm', 'now-Nh'",
            key="dql_timeframe_end"
        )
    with col3:
        max_results = st.number_input(
            "Maximum Result Records",
            min_value=1,
            max_value=10000,
            value=default_max_results,
            help="Maximum number of records to return from the query",
            key="dql_max_results"
        )

    output_format = st.radio(
        "Output Format",
        options=["Table", "JSON", "CSV"],
        index=0,
        horizontal=True,
        key="dql_output_format"
    )

    with st.expander("DQL Query Examples"):
        st.markdown("""
        ### Basic Examples
        ```
        fetch bizevents | limit 100
        ```
        ```
        fetch logs
        | filter matchesValue(content, "*error*")
        | limit 100
        ```
        ### Metric Examples
        ```
        timeseries dt.host.cpu.usage
        | fields host, os
        | limit 100
        ```
        ```
        timeseries dt.kubernetes.container.cpu_usage
        | sort avgHelper(-dt.kubernetes.container.cpu_usage)
        | limit 10
        ```
        """)

    if st.button("Run Query"):
        if not dql_query_text:
            st.error("Please enter a DQL query.")
        else:
            try:
                tf_start = iso8601(parse_time(timeframe_start))
                tf_end = iso8601(parse_time(timeframe_end))

                with st.spinner("Executing DQL query..."):
                    result = client.execute_dql_query(
                        query=dql_query_text,
                        timeframe_start=tf_start,
                        timeframe_end=tf_end,
                        max_result_records=int(max_results)
                    )

                if "result" in result:
                    records = result["result"].get("records", [])
                    metadata = result["result"].get("metadata", {})
                    if records:
                        st.success(f"Query executed successfully. Retrieved {len(records)} records.")

                        if metadata:
                            with st.expander("Query Metadata"):
                                st.json(metadata)

                        if output_format == "Table":
                            df_res = pd.DataFrame(records)
                            st.dataframe(df_res)

                            csv_data = df_res.to_csv(index=False)
                            st.download_button(
                                label="Download as CSV",
                                data=csv_data,
                                file_name="dql_results.csv",
                                mime="text/csv"
                            )

                        elif output_format == "JSON":
                            st.json(records)
                            json_str = json.dumps(records, indent=2)
                            st.download_button(
                                label="Download as JSON",
                                data=json_str,
                                file_name="dql_results.json",
                                mime="application/json"
                            )

                        else:
                            # CSV
                            keys = set()
                            for rec in records:
                                keys.update(rec.keys())
                            keys = sorted(keys)

                            csv_io = StringIO()
                            writer = csv.DictWriter(csv_io, fieldnames=keys)
                            writer.writeheader()
                            for rec in records:
                                writer.writerow({k: rec.get(k, "") for k in keys})

                            csv_str = csv_io.getvalue()
                            st.text_area("CSV Output", csv_str, height=300)
                            st.download_button(
                                label="Download Results as CSV",
                                data=csv_str,
                                file_name="dql_results.csv",
                                mime="text/csv"
                            )

                            if st.checkbox("Save to disk?"):
                                output_dir = config.get("settings", {}).get("output_dir", "output")
                                if not os.path.exists(output_dir):
                                    os.makedirs(output_dir)

                                file_name = st.text_input("File name:", "dql_results.csv")
                                file_path = os.path.join(output_dir, file_name)

                                if st.button("Save file"):
                                    with open(file_path, "w", newline="") as f:
                                        f.write(csv_str)
                                    st.success(f"Saved to {file_path}")
                    else:
                        st.info("Query executed, but no records returned.")
                else:
                    st.warning("Query returned unexpected format. Raw result:")
                    st.json(result)

            except Exception as e:
                st.error(f"Error executing query: {e}")
                st.error(traceback.format_exc())

    # Optionally allow saving current query to queries.yaml
    with st.expander("Save Current Query to queries.yaml"):
        query_name = st.text_input("Query Name", key="save_query_name")

        if st.button("Save Query"):
            if not query_name:
                st.error("Please enter a name for the query.")
            elif not dql_query_text:
                st.error("Query cannot be empty.")
            else:
                try:
                    current_queries = {}
                    try:
                        with open("queries.yaml", "r") as f:
                            import yaml
                            current_queries = yaml.safe_load(f) or {}
                    except FileNotFoundError:
                        pass

                    current_queries[query_name] = {
                        "query": dql_query_text,
                        "timeframe_start": timeframe_start,
                        "timeframe_end": timeframe_end,
                        "maxResultRecords": int(max_results)
                    }

                    with open("queries.yaml", "w") as f:
                        import yaml
                        yaml.dump(current_queries, f, default_flow_style=False)

                    st.success(f"Query '{query_name}' saved to queries.yaml!")
                except Exception as ex:
                    st.error(f"Error saving query: {ex}")
