# platform_client.py

import requests
from typing import Dict, List
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Disable the InsecureRequestWarning when verify=False
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class DynatracePlatformClient:
    """
    Client for Dynatrace Platform APIs using platform token authentication.
    SSL verification is disabled (verify=False) to allow self-signed certificates.
    """

    def __init__(self, base_url: str, platform_token: str):
        # Ensure we remove any trailing slash so we can safely append paths
        self.base_url = base_url.rstrip('/')
        self.platform_token = platform_token
        self.slo_api_path = "/platform/slo/v1"

        # Create a session so we only configure verify=False once
        self.session = requests.Session()
        self.session.verify = False  # ← DISABLE SSL CERT VERIFICATION
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.platform_token}"
        })

    def handle_response(self, response: requests.Response) -> Dict:
        if 200 <= response.status_code < 300:
            if response.status_code == 204:
                return {}
            return response.json() if response.content else {}
        else:
            raise Exception(f"Error {response.status_code}: {response.text}")

    # -------------------------
    # SLO API METHODS
    # -------------------------
    def list_slos(self, page_size: int = 100, page_key: str = None) -> Dict:
        url = f"{self.base_url}{self.slo_api_path}/slos"
        params = {"page-size": page_size}
        if page_key:
            params["page-key"] = page_key

        resp = self.session.get(url, params=params)
        return self.handle_response(resp)

    def delete_slo(self, slo_id: str, version: str) -> None:
        url = f"{self.base_url}{self.slo_api_path}/slos/{slo_id}"
        params = {"optimistic-locking-version": version}
        resp = self.session.delete(url, params=params)
        if resp.status_code != 204:
            self.handle_response(resp)

    def create_slo(self,
                   name: str,
                   description: str,
                   criteria: List[Dict],
                   custom_sli: Dict = None,
                   sli_reference: Dict = None,
                   tags: List[str] = None,
                   external_id: str = None) -> Dict:
        url = f"{self.base_url}{self.slo_api_path}/slos"
        payload = {
            "name": name,
            "description": description,
            "criteria": criteria
        }
        if custom_sli:
            payload["customSli"] = custom_sli
        if sli_reference:
            payload["sliReference"] = sli_reference
        if tags:
            payload["tags"] = tags
        if external_id:
            payload["externalId"] = external_id

        resp = self.session.post(url, json=payload)
        return self.handle_response(resp)

    def update_slo(self,
                   slo_id: str,
                   version: str,
                   name: str,
                   description: str,
                   criteria: List[Dict],
                   custom_sli: Dict = None,
                   sli_reference: Dict = None,
                   tags: List[str] = None,
                   external_id: str = None) -> Dict:
        """
        Update an existing SLO using the PUT endpoint
        """
        url = f"{self.base_url}{self.slo_api_path}/slos/{slo_id}"
        params = {"optimistic-locking-version": version}

        payload = {
            "name": name,
            "description": description,
            "criteria": criteria
        }
        if custom_sli:
            payload["customSli"] = custom_sli
        if sli_reference:
            payload["sliReference"] = sli_reference
        if tags:
            payload["tags"] = tags
        if external_id:
            payload["externalId"] = external_id

        resp = self.session.put(url, params=params, json=payload)
        return self.handle_response(resp)

    # -------------------------
    # DQL API METHOD
    # -------------------------
    def execute_dql_query(self,
                          query: str,
                          timeframe_start: str,
                          timeframe_end: str,
                          max_result_records: int = None) -> Dict:
        """
        Executes a DQL query against the Dynatrace DQL endpoint.
        """
        url = f"{self.base_url}/platform/storage/query/v1/query:execute"
        body = {
            "query": query,
            "requestTimeoutMilliseconds": 30000,
            "defaultTimeframeStart": timeframe_start,
            "defaultTimeframeEnd": timeframe_end
        }
        if max_result_records is not None:
            body["maxResultRecords"] = max_result_records

        response = self.session.post(url, json=body)
        return self.handle_response(response)
