# features/slo_create.py
import streamlit as st
import pandas as pd
from utils import robust_read_csv, parse_list_field
from async_utils import run_async_tasks
from async_platform_client import AsyncDynatracePlatformClient

# ===========================================================================
# Central Configuration for all SLO Types
# ===========================================================================
SLO_TYPE_CONFIG = {
    "Services": {
        "entity_column": "services",
        "name_template_default": "{app}_{bu}_{type}",
        "help_text": "Use placeholders like {app}, {type}, and any extra columns from your CSV.",
        "slo_options": {
            "Service Availability": {
                "type_code": "sa",
                "dql": """timeseries { total=sum(dt.service.request.count), failures=sum(dt.service.request.failure_count) }
  , by: { dt.entity.service }, filter: { in(dt.entity.service, { <PLACEHOLDER> }) }
| fieldsAdd sli=(((total[]-failures[])/total[])*(100)), entityName(dt.entity.service)
| fieldsRemove total, failures""",
            },
            "Service Performance": {
                "type_code": "sp",
                "dql": """timeseries total=avg(dt.service.request.response_time, default:0)
, by: { dt.entity.service }, filter: { in(dt.entity.service, { <PLACEHOLDER> }) }
| fieldsAdd high=iCollectArray(if(total[]>(1000*500), total[])), low=iCollectArray(if(total[]<=(1000*500), total[]))
| fieldsAdd highRespTimes=iCollectArray(if(isNull(high[]),0,else:1)), lowRespTimes=iCollectArray(if(isNull(low[]),0,else:1))
| fieldsAdd sli=100*(lowRespTimes[]/(lowRespTimes[]+highRespTimes[])), entityName(dt.entity.service)
| fieldsRemove total, high, low, highRespTimes, lowRespTimes""",
            },
        },
    },
    "Hosts": {
        "entity_column": "hosts",
        "name_template_default": "{app}_{bu}_{type}",
        "help_text": "Use placeholders like {app}, {type}, and any extra columns from your CSV.",
        "slo_options": {
            "Host CPU Usage": {
                "type_code": "hp",
                "dql": """timeseries sli=avg(dt.host.cpu.usage), by: { dt.entity.host }
, filter: in(dt.entity.host, { <PLACEHOLDER> })
| fieldsAdd entityName(dt.entity.host)""",
            },
        },
    },
    "K8s Clusters": {
        "entity_column": "id",
        "name_column": "entity.name",
        "name_template_default": "{cluster_name}",
        "help_text": "Use the {cluster_name} placeholder.",
        "slo_options": {
            "Kubernetes Cluster Memory Usage Efficiency": {
                "dql": """timeseries {
  requests_memory = sum(dt.kubernetes.container.requests_memory, rollup:avg),
  memory_allocatable = sum(dt.kubernetes.node.memory_allocatable, rollup:avg)
}, by:{dt.entity.kubernetes_cluster}, filter: IN(dt.entity.kubernetes_cluster, { <PLACEHOLDER> })
| fieldsAdd sli = (requests_memory[] / memory_allocatable[]) * 100, entityName(dt.entity.kubernetes_cluster)
| fieldsRemove requests_memory, memory_allocatable""",
            },
            "Kubernetes Cluster CPU Usage Efficiency": {
                "dql": """timeseries {
  requests_cpu = sum(dt.kubernetes.container.requests_cpu, rollup:avg),
  cpu_allocatable = sum(dt.kubernetes.node.cpu_allocatable, rollup:avg)
}, by:{dt.entity.kubernetes_cluster}, filter: IN(dt.entity.kubernetes_cluster, { <PLACEHOLDER> })
| fieldsAdd sli = (requests_cpu[] / cpu_allocatable[]) * 100, entityName(dt.entity.kubernetes_cluster)
| fieldsRemove requests_cpu, cpu_allocatable""",
            },
        },
    },
    "K8s Namespaces": {
        "is_grouped": True,
        "group_by_column": "k8s.cluster.name",
        "entity_column": "namespace",
        "name_template_default": "{cluster_name}",
        "help_text": "Use the {cluster_name} placeholder. One SLO will be created per cluster.",
        "slo_options": {
            "Kubernetes Namespace CPU Usage Efficiency": {
                "dql": """timeseries {
  cpuUsage = sum(dt.kubernetes.container.cpu_usage, default:0, rollup:avg),
  cpuRequest = sum(dt.kubernetes.container.requests_cpu, rollup:avg)
}, nonempty:true, by:{dt.entity.cloud_application_namespace}, filter: IN(dt.entity.cloud_application_namespace, { <PLACEHOLDER> })
| fieldsAdd sli = cpuUsage[] / cpuRequest[] * 100, entityName(dt.entity.cloud_application_namespace)
| fieldsRemove cpuUsage, cpuRequest""",
            },
            "Kubernetes Namespace Memory Usage Efficiency": {
                "dql": """timeseries {
  memWorkSet = sum(dt.kubernetes.container.memory_working_set, default:0, rollup:avg),
  memRequest = sum(dt.kubernetes.container.requests_memory, rollup:avg)
}, nonempty:true, by:{dt.entity.cloud_application_namespace}, filter: IN(dt.entity.cloud_application_namespace, { <PLACEHOLDER> })
| fieldsAdd sli = memWorkSet[] / memRequest[] * 100, entityName(dt.entity.cloud_application_namespace)
| fieldsRemove memWorkSet, memRequest""",
            },
        },
    },
    "Custom": {
        "entity_column": "app",
        "name_template_default": "{app}_{bu}",
        "help_text": "Creates one SLO per 'app' in the CSV, using the DQL filter.",
        "slo_options": {
            "Custom": {
                "type_code": "custom",
                "dql": """timeseries { total=sum(dt.service.request.count), failures=sum(dt.service.request.failure_count) },
by: { dt.entity.service },
filter: { matchesValue(entityAttr(dt.entity.service, "tags"), "DT-AppID:<PLACEHOLDER>") }
| fieldsAdd sli=(((total[]-failures[])/total[])*(100))
| fieldsAdd entityName(dt.entity.service)
| fieldsRemove total, failures""",
            },
        },
    },
}


# ===========================================================================
# Helper Function
# ===========================================================================

def generate_name_tags_description(row_data, df_cols, name_template, base_description):
    """Generates the final SLO name, tags, and description from a row of data."""
    tags, description_parts = [], []
    final_name = name_template

    for col_name in df_cols[2:]:
        if col_name in row_data and pd.notna(row_data[col_name]) and str(row_data[col_name]).strip() != "":
            col_value = str(row_data[col_name]).strip()
            placeholder = f"{{{col_name}}}"
            if placeholder in final_name:
                final_name = final_name.replace(placeholder, col_value)
            tags.append(f"{col_name}:{col_value}")
            description_parts.append(f"{col_name}={col_value}")

    extra_desc = ", ".join(description_parts)
    final_description = f"{base_description}, {extra_desc}" if extra_desc else base_description
    return final_name, tags, final_description


# ===========================================================================
# Main Streamlit UI Function
# ===========================================================================

def show_slo_create():
    """Renders the 'Create SLOs' tab."""
    st.header("Create SLOs From CSV")

    client = st.session_state.get("dt_client")
    csv_paths = st.session_state.get("csv_paths", {})
    if not client or not csv_paths:
        st.warning("Client or CSV paths not initialized in session state.")
        return

    # --- Step 1: Select CSV and SLO Type ---
    csv_choice = st.selectbox("Choose CSV for creation", list(csv_paths.keys()))
    creation_csv_path = csv_paths[csv_choice]

    config_key = next((k for k in SLO_TYPE_CONFIG if k in csv_choice), None)
    if not config_key:
        st.error(f"No configuration found for '{csv_choice}'. Please check SLO_TYPE_CONFIG.")
        return

    config = SLO_TYPE_CONFIG[config_key]
    slo_option_name = st.selectbox("Select SLO Type", list(config["slo_options"].keys()))
    slo_option_config = config["slo_options"][slo_option_name]

    # --- Step 2: Configure Naming and Criteria ---
    st.write("**SLO Naming Convention**")
    naming_convention = st.text_input(
        "Naming Format",
        value=config["name_template_default"],
        help=config["help_text"],
        key=f"naming_{config_key}"
    )
    dql_query = st.text_area("DQL Query Template", value=slo_option_config["dql"], height=200)

    st.write("**SLO Criteria**")
    c1, c2 = st.columns(2)
    target = c1.number_input("Target (%)", value=99.5, format="%.3f")
    warning = c2.number_input("Warning (%)", value=99.8, format="%.3f")
    timeframe_from = c1.text_input("Timeframe From", "now-7d")
    timeframe_to = c2.text_input("Timeframe To", "now")

    # --- Step 3: Create SLOs ---
    if st.button("Create SLOs from Selected CSV"):
        try:
            df = robust_read_csv(creation_csv_path)
            if df.empty:
                st.error("Could not read or process CSV file.")
                return
        except Exception as e:
            st.error(f"Error loading CSV '{creation_csv_path}': {e}")
            return

        criteria = [{"timeframeFrom": timeframe_from, "timeframeTo": timeframe_to, "target": float(target),
                     "warning": float(warning)}]

        st.write("---")
        st.info("Preparing SLOs for asynchronous creation...")

        # 1. Prepare all SLO creation parameters first
        slo_creation_params = []

        if config.get("is_grouped"):
            grouped = df.groupby(config["group_by_column"])
            for group_name, group in grouped:
                all_entities = []
                for _, row in group.iterrows():
                    all_entities.extend(parse_list_field(row[config["entity_column"]]))

                if not all_entities: continue

                MAX_ENTITIES = 40
                entity_chunks = [all_entities[i:i + MAX_ENTITIES] for i in
                                 range(0, len(all_entities), MAX_ENTITIES)]

                for i, chunk in enumerate(entity_chunks):
                    entity_str = ", ".join(f'"{e}"' for e in chunk)
                    final_dql = dql_query.replace("<PLACEHOLDER>", f"{{{entity_str}}}")

                    first_row_data = group.iloc[0].to_dict()
                    base_name = naming_convention.replace("{cluster_name}", str(group_name))
                    if len(entity_chunks) > 1:
                        base_name += f" - Part {i + 1}"

                    base_desc = f"{slo_option_name} for cluster: {group_name}"
                    name, tags, desc = generate_name_tags_description(first_row_data, df.columns, base_name,
                                                                      base_desc)
                    params = {"name": name, "description": desc, "criteria": criteria,
                              "custom_sli": {"indicator": final_dql}, "tags": tags}
                    slo_creation_params.append(params)

        else:  # Standard, one SLO per row
            for i, row in df.iterrows():
                row_data = row.to_dict()
                if config_key == "Custom":
                    entities = [str(row_data.get(config["entity_column"]))]
                else:
                    entities = parse_list_field(row_data.get(config["entity_column"]))

                if not entities: continue

                entity_str = entities[0] if config_key == "Custom" else ", ".join(f'"{e}"' for e in entities)
                final_dql = dql_query.replace("<PLACEHOLDER>", entity_str)

                if "K8s Clusters" in csv_choice:
                    cluster_name = str(row_data.get(config.get("name_column"), ""))
                    base_name = naming_convention.replace("{cluster_name}", cluster_name)
                    base_desc = f"K8s cluster usage: {cluster_name}"
                else:
                    app_name = str(row_data.get("app", ""))
                    bu_name = str(row_data.get("bu", ""))  # Get the 'bu' value from the row
                    type_code = slo_option_config.get("type_code", "slo")

                    # Replace {app}, {type}, and the new {bu} placeholder
                    base_name = naming_convention.replace("{app}", app_name).replace("{type}", type_code).replace(
                        "{bu}", bu_name)
                    base_desc = f"SLO for app={app_name}"

                name, tags, desc = generate_name_tags_description(row_data, df.columns, base_name, base_desc)
                params = {"name": name, "description": desc, "criteria": criteria,
                          "custom_sli": {"indicator": final_dql}, "tags": tags}
                slo_creation_params.append(params)

        if not slo_creation_params:
            st.warning("No SLOs to create based on the provided CSV.")
            return

        st.warning(f"Starting asynchronous creation of {len(slo_creation_params)} SLOs...")

        # 2. Create the list of async tasks
        async_client = AsyncDynatracePlatformClient(client.base_url, client.platform_token)
        tasks = [
            async_client.create_slo(
                name=p["name"],
                description=p["description"],
                criteria=p["criteria"],
                custom_sli=p["custom_sli"],
                tags=p["tags"]
            ) for p in slo_creation_params
        ]

        # 3. Run all tasks concurrently
        results = run_async_tasks(tasks)

        # 4. Process results
        created_count = 0
        for i, res in enumerate(results):
            slo_name = slo_creation_params[i].get('name')
            if isinstance(res, Exception):
                st.error(f"❌ Failed to create SLO '{slo_name}': {res}")
            else:
                st.write(f"✅ Created SLO: {slo_name} (ID: {res.get('id')})")
                created_count += 1

        st.success(f"Creation process finished. {created_count}/{len(slo_creation_params)} SLO(s) created.")