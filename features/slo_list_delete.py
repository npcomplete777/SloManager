# features/slo_list_delete.py
import streamlit as st
from utils import load_all_slos
from async_utils import run_async_tasks
from async_platform_client import AsyncDynatracePlatformClient


def _process_deletions(client, slos_to_delete):
    """
    Helper function to iterate through selected SLOs, delete them,
    and provide detailed feedback. Refreshes the SLO list in session state.
    """
    if not slos_to_delete:
        st.warning("No SLOs were selected for deletion.")
        return

    deleted_count = 0
    st.write("---")  # Separator for feedback
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

    if "all_slos" in st.session_state:
        all_slos = st.session_state["all_slos"]

        if not all_slos:
            st.info("The API call was made successfully, but there are no SLOs to load.")
            return

        st.info(f"**Total SLOs found: {len(all_slos)}**")
        st.write("---")

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
                    if st.session_state.get(f"del_{slo_id}"):
                        slos_to_delete.append((
                            slo_id,
                            slo.get("version"),
                            slo.get("name")
                        ))
                _process_deletions(client, slos_to_delete)
                # The st.rerun() call that was here has been removed.
                # The page will now wait for the next user action to refresh.

        st.write("---")
        st.subheader("Bulk Deletion")

        delete_all_bottom = st.button("🚨 Delete ALL SLOs", key="delete_all_bottom", use_container_width=True)
        confirm_delete_all = st.checkbox("I confirm I want to delete ALL loaded SLOs")

        if delete_all_bottom:
            if confirm_delete_all:
                st.write("---")
                st.warning("Starting asynchronous bulk deletion...")

                async_client = AsyncDynatracePlatformClient(client.base_url, client.platform_token)
                tasks = [
                    async_client.delete_slo(slo.get("id"), slo.get("version")) for slo in all_slos
                ]
                results = run_async_tasks(tasks)

                success_count = 0
                for i, res in enumerate(results):
                    slo_data = all_slos[i]
                    slo_name = slo_data.get('name', 'Unnamed')
                    slo_id = slo_data.get('id')
                    slo_version = slo_data.get('version')

                    if isinstance(res, Exception):
                        st.error(f"Error deleting {slo_name}: {res}")
                    else:
                        st.success(f"Deleted: **{slo_name}** (ID: {slo_id}, Version: {slo_version})")
                        success_count += 1

                st.info(f"Bulk deletion complete. {success_count}/{len(all_slos)} successful.")

                st.session_state["all_slos"] = []
                # The st.rerun() call that was here has been removed.
                # The feedback will now stay on the screen.
            else:
                st.warning("You must check the confirmation box to delete all SLOs.")