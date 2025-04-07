# features/slo_create.py

import streamlit as st
import pandas as pd
import ast
import os


####################################################
# Helper function to generate tags from columns[2:].
# (Identical to the final version used in main.py)
####################################################
def generate_tags_description_from_third_col(row, df, slo_name, naming_convention):
    """
    Given a row from the CSV, skip the first 2 columns
    and build a list of tags using columns[2:].
    Also applies any matching {col_name} placeholders
    inside the SLO naming convention.

    Returns:
        updated_slo_name (str): Possibly updated SLO name after placeholder replacements.
        tags (list): A list of tags derived from columns[2:].
        description (str): A descriptive string summarizing the columns used as tags.
    """
    tags = []
    description_parts = []

    # We start with the user-provided naming convention
    updated_slo_name = str(slo_name)

    # For each column from the 3rd onwards (index 2 and up):
    for col_name in df.columns[2:]:
        if col_name in row and pd.notna(row[col_name]) and str(row[col_name]).strip() != "":
            col_value = str(row[col_name]).strip()

            # If the naming convention has placeholders like {col_name}, replace them
            placeholder = f"{{{col_name}}}"
            if placeholder in updated_slo_name:
                updated_slo_name = updated_slo_name.replace(placeholder, col_value)

            # Add as a tag (key:value)
            tags.append(f"{col_name}:{col_value}")

            # For readability, add to description
            description_parts.append(f"{col_name}={col_value}")

    description = ", ".join(description_parts) if description_parts else ""
    return updated_slo_name, tags, description


def show_slo_create():
    """
    Full 'Create SLOs' tab logic.
    """
    st.header("Create SLOs From Pre-Loaded CSV")

    # Get the dt_client from session_state
    client = st.session_state["dt_client"]
    config = st.session_state["config"]
    csv_paths = st.session_state["csv_paths"]

    creation_csv_choice = st.selectbox("Choose CSV for creation", list(csv_paths.keys()))
    creation_csv_path = csv_paths[creation_csv_choice]

    # SLO naming
    st.write("**SLO Naming Convention**")
    if "K8s Namespaces" in creation_csv_choice or "K8s Clusters" in creation_csv_choice:
        naming_convention = st.text_input(
            "Naming Format",
            value="{cluster_name}",
            help="For K8s templates, use {cluster_name} placeholder",
            key="naming_convention_k8s"
        )
    else:
        naming_convention = st.text_input(
            "Naming Format",
            value="{app}_{type}",
            help="Use placeholders like {app}, {type}, and any additional columns from your CSV",
            key="naming_convention"
        )

    # We'll create a "default_dql" after we determine the SLO type
    default_dql = "fetch bizevents | limit 100"  # fallback

    # ---------- SERVICES ----------
    if "Services" in creation_csv_choice:
        service_slo_type = st.selectbox(
            "Service SLO Type",
            ["service availability", "service performance"],
            key="service_slo_type"
        )
        if "availability" in service_slo_type.lower():
            default_dql = """timeseries { total=sum(dt.service.request.count) ,failures=sum(dt.service.request.failure_count) }
  , by: { dt.entity.service }
  , filter: { in (dt.entity.service, { <PLACEHOLDER> }) }
| fieldsAdd sli=(((total[]-failures[])/total[])*(100))
| fieldsAdd entityName(dt.entity.service)
| fieldsRemove total, failures
"""
        else:
            default_dql = """timeseries total=avg(dt.service.request.response_time, default:0)
, by: { dt.entity.service }, filter: { in (dt.entity.service, { <PLACEHOLDER> }) }
| fieldsAdd high=iCollectArray(if(total[]> (1000 * 500), total[]))
| fieldsAdd low=iCollectArray(if(total[]<= (1000 * 500), total[]))
| fieldsAdd highRespTimes=iCollectArray(if(isNull(high[]),0,else:1))
| fieldsAdd lowRespTimes=iCollectArray(if(isNull(low[]),0,else:1))
| fieldsAdd sli=100*(lowRespTimes[]/(lowRespTimes[]+highRespTimes[]))
| fieldsAdd entityName(dt.entity.service)
| fieldsRemove total, high, low, highRespTimes, lowRespTimes
"""

    # ---------- K8s CLUSTERS ----------
    elif "K8s Clusters" in creation_csv_choice:
        cluster_slo_type = st.selectbox(
            "Cluster SLO Type",
            [
                "Kubernetes cluster memory usage efficiency",
                "Kubernetes cluster CPU usage efficiency"
            ],
            key="k8s_cluster_slo_type"
        )
        if "memory" in cluster_slo_type.lower():
            default_dql = """timeseries {
  requests_memory = sum(dt.kubernetes.container.requests_memory, rollup:avg),
  memory_allocatable = sum(dt.kubernetes.node.memory_allocatable, rollup:avg)
}, by:{dt.entity.kubernetes_cluster}
, filter: IN (dt.entity.kubernetes_cluster, { <PLACEHOLDER> })
| fieldsAdd sli = (requests_memory[] / memory_allocatable[]) * 100
| fieldsAdd entityName(dt.entity.kubernetes_cluster)
| fieldsRemove requests_memory, memory_allocatable
"""
        else:
            default_dql = """timeseries {
  requests_cpu = sum(dt.kubernetes.container.requests_cpu, rollup:avg),
  cpu_allocatable = sum(dt.kubernetes.node.cpu_allocatable, rollup:avg)
}, by:{dt.entity.kubernetes_cluster}
, filter: IN (dt.entity.kubernetes_cluster, { <PLACEHOLDER> })
| fieldsAdd sli = (requests_cpu[] / cpu_allocatable[]) * 100
| fieldsAdd entityName(dt.entity.kubernetes_cluster)
| fieldsRemove requests_cpu, cpu_allocatable
"""

    # ---------- K8s NAMESPACES ----------
    elif "K8s Namespaces" in creation_csv_choice:
        slo_type = st.selectbox(
            "Namespace SLO Type",
            ["Kubernetes namespace CPU usage efficiency", "Kubernetes namespace memory usage efficiency"],
            key="k8s_namespace_slo_type"
        )
        if "CPU" in slo_type:
            default_dql = """timeseries {
  cpuUsage = sum(dt.kubernetes.container.cpu_usage, default:0, rollup:avg),
  cpuRequest = sum(dt.kubernetes.container.requests_cpu, rollup:avg)
}, nonempty:true, by:{dt.entity.cloud_application_namespace}
, filter: IN(dt.entity.cloud_application_namespace, { <PLACEHOLDER> })
| fieldsAdd sli = cpuUsage[] / cpuRequest[] * 100
| fieldsAdd entityName(dt.entity.cloud_application_namespace)
| fieldsRemove cpuUsage, cpuRequest
"""
        else:
            default_dql = """timeseries {
  memWorkSet = sum(dt.kubernetes.container.memory_working_set, default:0, rollup:avg),
  memRequest = sum(dt.kubernetes.container.requests_memory, rollup:avg)
}, nonempty:true, by:{dt.entity.cloud_application_namespace}
, filter: IN(dt.entity.cloud_application_namespace, { <PLACEHOLDER> })
| fieldsAdd sli = memWorkSet[] / memRequest[] * 100
| fieldsAdd entityName(dt.entity.cloud_application_namespace)
| fieldsRemove memWorkSet, memRequest
"""

    # ---------- HOSTS ----------
    elif "Hosts" in creation_csv_choice:
        default_dql = """timeseries sli=avg(dt.host.cpu.usage)
, by: { dt.entity.host }
, filter: in(dt.entity.host, { <PLACEHOLDER> })
| fieldsAdd entityName(dt.entity.host)"""

    # The text area to allow editing the final DQL
    dql_query = st.text_area("DQL Query Template", value=default_dql, height=200)

    # SLO Criteria
    st.write("**SLO Criteria**")
    timeframe_from = st.text_input("Timeframe From", "now-7d")
    timeframe_to = st.text_input("Timeframe To", "now")
    target = st.number_input("Target (%)", value=99.5)
    warning = st.number_input("Warning (%)", value=99.8)

    if st.button("Create SLOs from Selected CSV"):
        try:
            df_create = pd.read_csv(creation_csv_path)
        except Exception as e:
            st.error(f"Error loading CSV: {e}")
            return

        criteria = [{
            "timeframeFrom": timeframe_from,
            "timeframeTo": timeframe_to,
            "target": float(target),
            "warning": float(warning)
        }]
        created_count = 0

        ##################
        # SERVICES
        ##################
        if "Services" in creation_csv_choice:
            # Verify required columns
            required_cols = ["app", "services"]
            missing = [c for c in required_cols if c not in df_create.columns]
            if missing:
                st.error(f"Missing required columns: {missing}")
            else:
                service_slo_type = st.session_state.get("service_slo_type", "service availability")
                for i, row in df_create.iterrows():
                    # Get services list
                    raw_val = row["services"]
                    try:
                        services_list = ast.literal_eval(raw_val)
                        if not isinstance(services_list, list):
                            services_list = [services_list]
                    except:
                        services_list = [raw_val]

                    # Insert each service ID with quotes
                    services_str = ", ".join(f"\"{s}\"" for s in services_list)
                    final_dql = dql_query.replace("<PLACEHOLDER>", services_str)
                    custom_sli = {"indicator": final_dql}

                    # Base naming placeholders
                    app_str = str(row["app"]).strip()
                    # Start with user naming convention
                    slo_name = naming_convention.replace("{app}", app_str)
                    # For service type code (sa or sp)
                    service_type_code = "sa" if "availability" in service_slo_type.lower() else "sp"
                    slo_name = slo_name.replace("{type}", service_type_code)

                    # Build tags from columns[2:] only
                    row_dict = row.to_dict()
                    updated_slo_name, tags, tags_desc = generate_tags_description_from_third_col(
                        row_dict, df_create, slo_name, naming_convention
                    )

                    # Combine base description plus any extra tags
                    description = f"SLO for app={app_str}"
                    if tags_desc:
                        description += f", {tags_desc}"

                    # Actually create the SLO
                    try:
                        new_slo = client.create_slo(
                            name=updated_slo_name,
                            description=description,
                            criteria=criteria,
                            custom_sli=custom_sli,
                            tags=tags
                        )
                        created_count += 1
                        st.write(f"Row {i}: Created SLO ID={new_slo.get('id')}")
                    except Exception as ex:
                        st.error(f"Row {i} failed: {ex}")

        ##################
        # HOSTS
        ##################
        elif "Hosts" in creation_csv_choice:
            required_cols = ["app", "hosts"]
            missing = [c for c in required_cols if c not in df_create.columns]
            if missing:
                st.error(f"Missing required columns: {missing}")
            else:
                for i, row in df_create.iterrows():
                    raw_val = row["hosts"]
                    try:
                        hosts_list = ast.literal_eval(raw_val)
                        if not isinstance(hosts_list, list):
                            hosts_list = [hosts_list]
                    except:
                        hosts_list = [raw_val]

                    hosts_str = ", ".join(f"\"{h}\"" for h in hosts_list)
                    final_dql = dql_query.replace("<PLACEHOLDER>", hosts_str)
                    custom_sli = {"indicator": final_dql}

                    app_str = str(row["app"]).strip()
                    slo_name = naming_convention.replace("{app}", app_str)
                    # "hp" for host performance
                    slo_name = slo_name.replace("{type}", "hp")

                    row_dict = row.to_dict()
                    updated_slo_name, tags, tags_desc = generate_tags_description_from_third_col(
                        row_dict, df_create, slo_name, naming_convention
                    )

                    description = f"SLO for app={app_str}"
                    if tags_desc:
                        description += f", {tags_desc}"

                    try:
                        new_slo = client.create_slo(
                            name=updated_slo_name,
                            description=description,
                            criteria=criteria,
                            custom_sli=custom_sli,
                            tags=tags
                        )
                        created_count += 1
                        st.write(f"Row {i}: Created SLO ID={new_slo.get('id')}")
                    except Exception as ex:
                        st.error(f"Row {i} failed: {ex}")

        ##################
        # K8s CLUSTERS
        ##################
        elif "K8s Clusters" in creation_csv_choice:
            required_cols = ["entity.name", "id"]
            missing = [c for c in required_cols if c not in df_create.columns]
            if missing:
                st.error(f"Missing required columns: {missing}")
            else:
                for i, row in df_create.iterrows():
                    cluster_name = str(row["entity.name"]).strip()
                    cluster_id = str(row["id"]).strip()

                    final_dql = dql_query.replace("<PLACEHOLDER>", f"\"{cluster_id}\"")
                    custom_sli = {"indicator": final_dql}

                    base_slo_name = naming_convention.replace("{cluster_name}", cluster_name).strip()
                    row_dict = row.to_dict()

                    updated_slo_name, tags, tags_desc = generate_tags_description_from_third_col(
                        row_dict, df_create, base_slo_name, naming_convention
                    )

                    description = f"K8s cluster usage: {cluster_name}"
                    if tags_desc:
                        description += f", {tags_desc}"

                    try:
                        new_slo = client.create_slo(
                            name=updated_slo_name,
                            description=description,
                            criteria=criteria,
                            custom_sli=custom_sli,
                            tags=tags
                        )
                        created_count += 1
                        st.write(f"Row {i}: Created K8s SLO ID={new_slo.get('id')}")
                    except Exception as ex:
                        st.error(f"Row {i} failed: {ex}")

        ##################
        # K8s NAMESPACES
        ##################
        elif "K8s Namespaces" in creation_csv_choice:
            required_cols = ["k8s.cluster.name", "namespace"]
            missing = [c for c in required_cols if c not in df_create.columns]
            if missing:
                st.error(f"Missing required columns: {missing}")
            else:
                grouped = df_create.groupby("k8s.cluster.name")
                slo_type = st.session_state.get("k8s_namespace_slo_type",
                                                "Kubernetes namespace CPU usage efficiency")
                type_abbr = "cpu" if "CPU" in slo_type else "mem"

                for cluster_name, group in grouped:
                    all_namespaces = []
                    for _, row_ns in group.iterrows():
                        raw_val = str(row_ns["namespace"]).strip()
                        try:
                            ns_list = ast.literal_eval(raw_val)
                            if not isinstance(ns_list, list):
                                ns_list = [ns_list]
                        except:
                            ns_list = [raw_val]
                        all_namespaces.extend(ns_list)

                    # remove duplicates if needed
                    clean_ns_list = list({ns.strip() for ns in all_namespaces})
                    # each ID must be quoted individually
                    inner_ns = ", ".join(f"\"{ns}\"" for ns in clean_ns_list)
                    namespace_ids_formatted = f'{{ {inner_ns} }}'

                    final_dql = dql_query.replace("<PLACEHOLDER>", namespace_ids_formatted)
                    custom_sli = {"indicator": final_dql}

                    base_slo_name = naming_convention.replace("{cluster_name}", cluster_name).strip()

                    first_row = group.iloc[0]
                    row_dict = first_row.to_dict()
                    updated_slo_name, tags, tags_desc = generate_tags_description_from_third_col(
                        row_dict, df_create, base_slo_name, naming_convention
                    )

                    description = f"{slo_type} for cluster: {cluster_name}"
                    if tags_desc:
                        description += f", {tags_desc}"

                    try:
                        st.write(f"Creating SLO for cluster {cluster_name}")
                        new_slo = client.create_slo(
                            name=updated_slo_name,
                            description=description,
                            criteria=criteria,
                            custom_sli=custom_sli,
                            tags=tags
                        )
                        created_count += 1
                        st.write(f"Created {slo_type} SLO for cluster {cluster_name}, ID={new_slo.get('id')}")
                    except Exception as ex:
                        st.error(f"Error creating SLO for cluster {cluster_name}: {ex}")
                        st.error("Failed DQL query:")
                        st.code(final_dql, language="sql")

        st.success(f"Creation finished. {created_count} SLO(s) created.")

