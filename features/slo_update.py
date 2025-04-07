# features/slo_update.py

import streamlit as st

def show_slo_update():
    st.header("Update Existing SLOs")

    client = st.session_state["dt_client"]

    # Refresh SLO list if needed
    if "all_slos" not in st.session_state or st.button("Refresh SLO List", key="refresh_slos_update"):
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
            st.success(f"Loaded {len(all_slos)} SLOs.")
        except Exception as e:
            st.error(f"Error loading SLOs: {e}")

    # If we have the SLOs, let user select one
    if "all_slos" in st.session_state and st.session_state["all_slos"]:
        all_slos = st.session_state["all_slos"]

        slo_options = [f"{s.get('name')} (ID: {s.get('id')})" for s in all_slos]
        selected_slo_option = st.selectbox("Select SLO to update:", slo_options, key="slo_selector")

        selected_slo_id = selected_slo_option.split("(ID: ")[1].split(")")[0]
        selected_slo = next((s for s in all_slos if s.get('id') == selected_slo_id), None)

        if selected_slo:
            with st.expander("Current SLO Details"):
                st.json(selected_slo)

            st.write("**Update SLO Fields:**")

            new_name = st.text_input("Name", value=selected_slo.get('name', ''), key="update_name")
            new_description = st.text_input("Description", value=selected_slo.get('description', ''),
                                            key="update_description")

            custom_sli = selected_slo.get('customSli', {})
            new_indicator = st.text_area(
                "DQL Query",
                value=custom_sli.get('indicator', ''),
                height=200,
                key="update_indicator"
            )

            criteria = selected_slo.get('criteria', [{}])
            if not criteria:
                criteria = [{}]
            c0 = criteria[0]
            new_timeframe_from = st.text_input("Timeframe From", value=c0.get('timeframeFrom', 'now-7d'),
                                               key="update_timeframe_from")
            new_timeframe_to = st.text_input("Timeframe To", value=c0.get('timeframeTo', 'now'),
                                             key="update_timeframe_to")
            new_target = st.number_input("Target (%)", value=c0.get('target', 99.5), key="update_target")
            new_warning = st.number_input("Warning (%)", value=c0.get('warning', 99.8), key="update_warning")

            current_tags = selected_slo.get('tags', [])
            current_tags_str = "\n".join(current_tags)
            new_tags_str = st.text_area(
                "Tags (one per line)",
                value=current_tags_str,
                help="Enter tags in format 'key:value', one per line",
                key="update_tags"
            )
            new_tags = [tag.strip() for tag in new_tags_str.split("\n") if tag.strip()]

            if st.button("Update SLO"):
                try:
                    updated_criteria = [{
                        "timeframeFrom": new_timeframe_from,
                        "timeframeTo": new_timeframe_to,
                        "target": float(new_target),
                        "warning": float(new_warning)
                    }]

                    updated_custom_sli = {"indicator": new_indicator}
                    version = selected_slo.get('version')

                    with st.spinner("Updating SLO..."):
                        _ = client.update_slo(
                            slo_id=selected_slo_id,
                            version=version,
                            name=new_name,
                            description=new_description,
                            criteria=updated_criteria,
                            custom_sli=updated_custom_sli,
                            tags=new_tags,
                            external_id=selected_slo.get('externalId')
                        )

                    st.success(f"Successfully updated SLO: {new_name}")

                    # Refresh SLO list
                    with st.spinner("Refreshing SLO list..."):
                        updated_slos = []
                        page_key = None
                        while True:
                            resp_js = client.list_slos(page_size=200, page_key=page_key)
                            items_new = resp_js.get("slos", [])
                            updated_slos.extend(items_new)
                            page_key = resp_js.get("nextPageKey")
                            if not page_key:
                                break
                        st.session_state["all_slos"] = updated_slos

                except Exception as ex:
                    st.error(f"Error updating SLO: {ex}")
        else:
            st.error("Selected SLO not found.")
    else:
        st.warning("No SLOs loaded. Click 'Refresh SLO List' to load SLOs.")
