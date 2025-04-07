import requests

class DQLClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.token = token

    def fetch_dql_data(self, query, timeFrameStart, timeFrameEnd, max_records=100):
        """
        Execute a DQL query against Dynatrace.
        """
        headers = {
            "Authorization": f"Api-Token {self.token}",
            "Content-Type": "application/json",
        }

        payload = {
            "query": query,
            "timeFrameStart": timeFrameStart,
            "timeFrameEnd": timeFrameEnd,
            "maxResults": max_records
        }

        # Replace with your real Dynatrace DQL endpoint
        url = f"{self.base_url}/api/v2/metrics/xyz/dql"

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code != 200:
            raise Exception(f"DQL query failed: {response.text}")

        return response.json()
