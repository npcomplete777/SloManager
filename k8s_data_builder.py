# k8s_data_builder.py

import pandas as pd
from io import StringIO

# Import the same parse_time & iso8601 that your main app uses
from utils import parse_time, iso8601

def build_k8s_inventory_csv(client,
                            timeframe_start="now-24h",
                            timeframe_end="now",
                            output_csv="k8s_inventory.csv"):
    """
    Gathers K8s data across all clusters, returning a final DataFrame and
    optionally writing to CSV. Each row will represent one cluster:
      - clusterName
      - clusterID
      - nodeNames (list[str])
      - nodeIDs   (list[str])
      - namespaceNames (list[str])
      - namespaceIDs   (list[str])
    """

    # 1) Convert relative times (now-24h, now, etc.) to absolute ISO8601
    try:
        ts_start = iso8601(parse_time(timeframe_start))
        ts_end = iso8601(parse_time(timeframe_end))
    except Exception as ex:
        raise ValueError(
            f"Invalid timeframe: '{timeframe_start}' -> '{timeframe_end}'. Reason: {ex}"
        )

    # 2) Fetch cluster name + ID
    cluster_query = "fetch dt.entity.kubernetes_cluster"
    cluster_resp = client.execute_dql_query(
        query=cluster_query,
        timeframe_start=ts_start,
        timeframe_end=ts_end
    )
    cluster_records = cluster_resp.get("result", {}).get("records", [])

    cluster_data = []
    for rec in cluster_records:
        c_name = rec.get("entity.name", "")
        c_id = rec.get("id", "")
        if c_name:
            cluster_data.append((c_name, c_id))

    # 3) For each cluster, fetch nodes + namespaces
    final_rows = []
    for (c_name, c_id) in cluster_data:
        # Escape quotes in cluster name
        c_name_escaped = c_name.replace('"','\\"')

        # --- NODES ---
        node_query = f"""
fetch dt.entity.kubernetes_node
| fields entity.name, id
| filter in(id, classicEntitySelector(concat(
    "type(KUBERNETES_NODE),toRelationship.isClusterOfNode(type(KUBERNETES_CLUSTER),entityName.equals(\\"{c_name_escaped}\\"))"
)))
"""
        node_resp = client.execute_dql_query(
            query=node_query,
            timeframe_start=ts_start,
            timeframe_end=ts_end
        )
        node_records = node_resp.get("result", {}).get("records", [])
        node_names = [r.get("entity.name", "") for r in node_records]
        node_ids = [r.get("id", "") for r in node_records]

        # --- NAMESPACES ---
        namespace_query = f"""
fetch dt.entity.cloud_application_namespace
| filter in(id, classicEntitySelector(concat(
    "type(CLOUD_APPLICATION_NAMESPACE),toRelationship.isClusterOfNamespace(type(KUBERNETES_CLUSTER),entityName.equals(\\"{c_name_escaped}\\"))"
)))
| fields entity.name, id
"""
        ns_resp = client.execute_dql_query(
            query=namespace_query,
            timeframe_start=ts_start,
            timeframe_end=ts_end
        )
        ns_records = ns_resp.get("result", {}).get("records", [])
        ns_names = [r.get("entity.name", "") for r in ns_records]
        ns_ids = [r.get("id", "") for r in ns_records]

        final_rows.append({
            "clusterName": c_name,
            "clusterID": c_id,
            "nodeNames": node_names,
            "nodeIDs": node_ids,
            "namespaceNames": ns_names,
            "namespaceIDs": ns_ids
        })

    # 4) Convert to DataFrame + save CSV
    df = pd.DataFrame(final_rows)
    df.to_csv(output_csv, index=False)
    return df
