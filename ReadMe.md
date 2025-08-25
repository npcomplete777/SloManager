# SLO Generator Tool

## Program Structure

```
my_app/
├── main.py                       # Minimal Streamlit entry point
├── features/
│   ├── csv_manager.py           # Tab 1 code
│   ├── slo_list_delete.py       # Tab 2 code
│   ├── slo_create.py            # Tab 3 code
│   ├── slo_update.py            # Tab 4 code
│   ├── dql_queries.py           # Tab 5 code
│   └── k8s_inventory.py         # Tab 6 code
├── platform_client.py           # Platform API integration
├── template_manager.py          # SLO template handling
├── ui_components.py             # Shared UI elements
├── utils.py                     # Helper functions
├── data_processing.py           # Data processing utilities
├── dql_client.py                # DQL API client
├── queries.py                   # Query management
├── queries.yaml                 # Query definitions
├── ZURICH_APPS_SERVICES_WITH_TAGS.csv
├── ZURICH_APPS_CUSTOM.csv
├── ZURICH_HOSTS_WITH_TAGS.csv
├── ZURICH_K8s_CLUSTERS.csv
├── ZURICH_K8s_NAMESPACES_BY_CLUSTER.csv
└── requirements.txt
```

## Getting Started

### Prerequisites

- Python 3.x

### Installation

1. **Check Python version**
   ```
   python --version
   ```

2. **Clone or download the repository**
   ```
   cd path/to/your/project
   ```

3. **Create and activate a virtual environment**
   
   On macOS/Linux:
   ```
   python -m venv venv
   source venv/bin/activate
   ```
   
   On Windows:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

4. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

5. **Run the Streamlit application**
   ```
   streamlit run main.py
   ```

## SLO Naming Format

On the 'Create SLOs' tab, the "Naming Format" field allows you to define how SLOs will be named.

### Naming Format Templates

The naming format is a template string that generates a descriptive name for each SLO. The template uses placeholders enclosed in curly braces `{}` that are replaced by values from your CSV data or UI selections.

#### Default Templates

**For Non-K8s SLOs (Services, Hosts):**
```
{app}_{type}
```
Where:
- `{app}` is replaced by the value in the CSV column named 'app'
- `{type}` is replaced by a code based on your selection:
  - Services: "sa" for availability or "sp" for performance
  - Hosts: "hp" for host performance
  - Custom: "custom" for using the custom template option

**For K8s Templates (Clusters and Namespaces):**
```
{cluster_name}
```
Where:
- `{cluster_name}` is replaced by the value in the CSV column that identifies the cluster

### Using Additional Placeholders

**Extra CSV Columns:**
Any extra columns in your CSV (from the 3rd column onward) can be used to:
- Append tags to the SLO (for filtering in Dynatrace)
- Replace matching placeholders in the naming format

For example, if your CSV contains a column named 'region' and your naming format is:
```
{app}_{region}_{type}
```
Then `{region}` will be replaced by the corresponding value from that column.

### How the Naming System Works

1. **Initial Template:**
   The system starts with your provided naming format template

2. **Primary Replacements:**
   First replaces placeholders like `{app}` or `{cluster_name}` using required CSV columns or UI selections

3. **Extra Replacements:**
   For every extra column in the CSV, the system checks if the naming template contains a matching placeholder

4. **Resulting Name:**
   The final SLO name becomes both a unique identifier and a human-readable description

### Examples

**Example 1: Service CSV**
- CSV columns: app, services, region
- Naming format: `{app}_{region}_{type}`
- Row data: app="Inventory", services=["service1", "service2"], region="US"
- Selection: service availability (sets {type} to "sa")
- Result: `Inventory_US_sa`

**Example 2: K8s Namespaces CSV**
- Naming format: `{cluster_name}_{env}`
- Row data: cluster_name="DoksCluster", env="prod"
- Result: `DoksCluster_prod`

### Customizing the Naming Format

**Flexibility:**
You can modify the template to include any placeholders that match your CSV column names

**Consistency:**
Ensure that your CSV headers match the placeholder names you want to use (case-sensitive)

You can adjust the naming format to suit your organization's naming standards or to include additional contextual information from your CSV.




Queries for creating CSV templates for Hosts and Services:

// query to show Zurich tags for Services in a table 
fetch dt.entity.service
| fieldsAdd app = splitString(
    splitString(toString(tags), "DT-AppID:")[1], 
    "\""
  )[0]
| fieldsAdd env = splitString(
    splitString(toString(tags), "DT-AppEnv:")[1], 
    "\""
  )[0]
| fieldsAdd criticality = splitString(
    splitString(toString(tags), "DT-Criticality:")[1], 
    "\""
  )[0]
| fieldsAdd bu = splitString(
    splitString(toString(tags), "DT-BusinessUnit:")[1], 
    "\""
  )[0]
| filter contains(env, "PRD")
| summarize 
{
    services    = collectDistinct(id),
    env         = takeAny(env),
    criticality = takeAny(criticality),
    bu          = takeAny(bu)
},
    by: { app }



// query to show Zurich tags for Hosts in a table 
fetch dt.entity.host
| fieldsAdd app = splitString(
    splitString(toString(tags), "DT-AppID:")[1], 
    "\""
  )[0]
| fieldsAdd env = splitString(
    splitString(toString(tags), "DT-AppEnv:")[1], 
    "\""
  )[0]
| fieldsAdd criticality = splitString(
    splitString(toString(tags), "DT-Criticality:")[1], 
    "\""
  )[0]
| fieldsAdd bu = splitString(
    splitString(toString(tags), "DT-BusinessUnit:")[1], 
    "\""
  )[0]
| filter contains(env, "PRD")
| summarize 
{
    services    = collectDistinct(id),
    env         = takeAny(env),
    criticality = takeAny(criticality),
    bu          = takeAny(bu)
},
    by: { app }
