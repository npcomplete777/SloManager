# features/csv_manager.py

import streamlit as st
import pandas as pd
import os

def show_csv_manager():
    st.header("Manage Default CSV Paths")

    # Access the dictionary of CSV paths from session state.
    csv_paths = st.session_state["csv_paths"]

    # Let the user select a CSV file.
    csv_choice = st.selectbox("Select CSV to view/edit:", list(csv_paths.keys()))
    current_path = csv_paths[csv_choice]
    new_path = st.text_input("CSV File Path", value=current_path, key=f"csv_path_{csv_choice}")
    st.session_state["csv_paths"][csv_choice] = new_path

    # Button to load and preview the selected CSV.
    if st.button("Load & Preview Selected CSV"):
        try:
            df = pd.read_csv(new_path)
            st.session_state["preview_df"] = df
            st.success(f"Loaded CSV from {new_path}")
        except Exception as e:
            st.error(f"Error reading CSV at path '{new_path}': {e}")

    # If a preview DataFrame is loaded, allow editing.
    if "preview_df" in st.session_state:
        st.write("### Edit CSV Data")
        # Use st.data_editor if available; otherwise, fallback to experimental_data_editor.
        if hasattr(st, "data_editor"):
            edited_df = st.data_editor(
                st.session_state["preview_df"],
                num_rows="dynamic",
                key="csv_editor"
            )
        else:
            edited_df = st.experimental_data_editor(
                st.session_state["preview_df"],
                num_rows="dynamic",
                key="csv_editor"
            )
        # Update the session state with the edited data.
        st.session_state["preview_df"] = edited_df

        st.write("---")
        st.write("### Save Edited CSV as New Template")
        new_template_name = st.text_input(
            "Enter new template file name (e.g., new_template.csv):",
            key="new_template_name"
        )
        if st.button("Save Edited CSV as New Template"):
            if new_template_name.strip() == "":
                st.error("Please provide a valid file name for the new template.")
            else:
                try:
                    edited_df.to_csv(new_template_name, index=False)
                    # Optionally, add the new template to csv_paths for future selection.
                    st.session_state["csv_paths"][new_template_name] = new_template_name
                    st.success(f"Saved edited CSV as new template: {new_template_name}")
                except Exception as e:
                    st.error(f"Error saving new template: {e}")

    st.write("---")
    st.write("Or upload a new CSV to replace the default:")
    uploaded_new_csv = st.file_uploader("Upload CSV", type="csv", key=f"uploader_{csv_choice}")
    if uploaded_new_csv is not None:
        new_local_name = os.path.basename(uploaded_new_csv.name)
        try:
            with open(new_local_name, "wb") as f:
                f.write(uploaded_new_csv.read())
            st.session_state["csv_paths"][csv_choice] = new_local_name
            st.success(f"Uploaded new CSV and updated path to {new_local_name}")
        except Exception as e:
            st.error(f"Error saving uploaded CSV: {e}")
