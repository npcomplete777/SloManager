# features/slo_list_delete.py

import streamlit as st

def show_slo_list_delete():
    st.header("List and Delete SLOs")

    # We expect a dt_client in session_state
    client = st.session_state["dt_client"]

    if st.button("Load All SLOs"):
        try:
            all_slos = []
            page_key = None
            with st.spinner("Loading SLOs..."):
                while True:
                    response_json = client.list_slos(page_size=200, page_key=page_key)
                    items = response_json.get("slos", [])
                    all_slos.extend(items)
                    page_key = response_json.get("nextPageKey")
                    if not page_key:
                        break
            st.session_state["all_slos"] = all_slos
            st.success(f"Successfully loaded {len(all_slos)} SLOs.")
        except Exception as e:
            st.error(f"Error loading SLOs: {e}")

    if "all_slos" in st.session_state:
        all_slos = st.session_state["all_slos"]
        st.write(f"Total SLOs found: {len(all_slos)}")

        if all_slos:
            to_delete = []
            for i, slo_data in enumerate(all_slos):
                slo_name = slo_data.get("name", "Unnamed")
                slo_id = slo_data.get("id", "")
                version = slo_data.get("version", "")

                col1, col2, col3 = st.columns([0.05, 0.6, 0.35])
                with col1:
                    checked = st.checkbox("", key=f"slo_del_{i}")
                    if checked:
                        to_delete.append((slo_id, version, slo_name))
                with col2:
                    st.write(f"**{slo_name}**")
                with col3:
                    st.write(f"ID: {slo_id}, Ver: {version}")

            if to_delete and st.button("Delete Selected SLOs"):
                for (s_id, s_ver, s_name) in to_delete:
                    try:
                        client.delete_slo(s_id, s_ver)
                        st.write(f"Deleted {s_name} (ID={s_id})")
                    except Exception as ex:
                        st.error(f"Error deleting {s_name}: {ex}")

                # Refresh the list after deletion
                with st.spinner("Refreshing SLO list..."):
                    all_slos = []
                    page_key = None
                    while True:
                        resp_json = client.list_slos(page_size=200, page_key=page_key)
                        items2 = resp_json.get("slos", [])
                        all_slos.extend(items2)
                        page_key = resp_json.get("nextPageKey")
                        if not page_key:
                            break
                    st.session_state["all_slos"] = all_slos
                    st.success("SLO list refreshed.")

            # Show a checkbox for "Delete ALL SLOs" confirmation
            delete_confirm = st.checkbox("I confirm I want to delete ALL SLOs", key="delete_all_confirm")

            if delete_confirm and st.button("Delete ALL SLOs"):
                with st.spinner("Deleting all SLOs..."):
                    for slo_data in all_slos:
                        sid = slo_data.get("id")
                        ver = slo_data.get("version")
                        name = slo_data.get("name", "Unnamed")
                        try:
                            client.delete_slo(sid, ver)
                            st.write(f"Deleted {name}")
                        except Exception as ex:
                            st.error(f"Error deleting {name}: {ex}")
                st.session_state["all_slos"] = []
                st.success("All SLOs deleted.")
