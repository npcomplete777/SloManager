import streamlit as st
from utils import load_all_slos


def _process_deletions(client, slos_to_delete):
    """
    Helper function to iterate through selected SLOs, delete them,
    and provide detailed feedback.
    """
    if not slos_to_delete:
        st.warning("No SLOs were selected for deletion.")
        return

    deleted_count = 0
    for s_id, s_ver, s_name in slos_to_delete:
        try:
            client.delete_slo(s_id, s_ver)
            st.success(f"Deleted: **{s_name}** (ID: {s_id}, Version: {s_ver})")
            deleted_count += 1
        except Exception as ex:
            st.error(f"Error deleting {s_name}: {ex}")

    if deleted_count > 0:
        with st.spinner("Refreshing SLO list..."):
            st.session_state["all_slos"] = load_all_slos(client)


def show_slo_list_delete():
    st.header("List and Delete SLOs")

    client = st.session_state["dt_client"]

    if st.button("Load All SLOs"):
        with st.spinner("Loading SLOs..."):
            st.session_state["all_slos"] = load_all_slos(client)
        st.success(f"Successfully loaded {len(st.session_state.get('all_slos', []))} SLOs.")
        st.rerun()

    if "all_slos" in st.session_state and st.session_state["all_slos"]:
        all_slos = st.session_state["all_slos"]

        # --- TOP "DELETE ALL" SECTION ---
        col1, col2 = st.columns([0.7, 0.3])
        col1.info(f"**Total SLOs found: {len(all_slos)}**")
        delete_all_top = col2.button("🚨 Delete ALL SLOs", key="delete_all_top", use_container_width=True)
        st.write("---")

        # Section for Deleting Selected SLOs (using a form)
        with st.form(key="delete_selected_form"):
            st.subheader("Delete Selected SLOs")
            st.write("Select individual SLOs below and click the button at the bottom to delete them.")

            for slo_data in all_slos:
                slo_id = slo_data.get("id", "")
                slo_name = slo_data.get("name", "Unnamed")

                check_col, expander_col = st.columns([0.05, 0.95])
                with check_col:
                    st.checkbox(" ", key=f"del_{slo_id}", label_visibility="collapsed")
                with expander_col:
                    with st.expander(f"**{slo_name}**"):
                        st.json(slo_data)

            submitted_selected = st.form_submit_button(
                "Delete Selected SLOs",
                use_container_width=True,
                type="primary"
            )

            if submitted_selected:
                slos_to_delete = []
                for slo in all_slos:
                    slo_id = slo.get("id")
                    if st.session_state[f"del_{slo_id}"]:
                        slos_to_delete.append((
                            slo_id,
                            slo.get("version"),
                            slo.get("name")
                        ))
                _process_deletions(client, slos_to_delete)
                st.rerun()

        # --- BOTTOM "DELETE ALL" SECTION ---
        st.write("---")
        st.subheader("Bulk Deletion")

        delete_all_bottom = st.button("🚨 Delete ALL SLOs", key="delete_all_bottom", use_container_width=True)

        confirm_delete_all = st.checkbox("I confirm I want to delete ALL loaded SLOs")

        if delete_all_top or delete_all_bottom:
            if confirm_delete_all:
                with st.spinner("Deleting all SLOs..."):
                    for slo_data in all_slos:
                        sid = slo_data.get("id")
                        ver = slo_data.get("version")
                        name = slo_data.get("name", "Unnamed")
                        try:
                            client.delete_slo(sid, ver)
                            st.success(f"Deleted: **{name}** (ID: {sid})")
                        except Exception as ex:
                            st.error(f"Error deleting {name}: {ex}")
                st.session_state["all_slos"] = []
                st.success("All SLOs have been deleted.")
                st.rerun()
            else:
                st.warning("You must check the confirmation box to delete all SLOs.")