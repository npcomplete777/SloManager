# async_platform_client.py
import httpx
from typing import Dict, List


class AsyncDynatracePlatformClient:
    """
    Asynchronous client for Dynatrace Platform APIs.
    """

    def __init__(self, base_url: str, platform_token: str):
        self.base_url = base_url.rstrip('/')
        self.platform_token = platform_token
        self.slo_api_path = "/platform/slo/v1"
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.platform_token}"
        }

    async def handle_async_response(self, response: httpx.Response) -> Dict:
        if 200 <= response.status_code < 300:
            if response.status_code == 204:
                return {}
            return response.json() if response.content else {}
        else:
            response.raise_for_status()

    async def delete_slo(self, slo_id: str, version: str) -> None:
        url = f"{self.base_url}{self.slo_api_path}/slos/{slo_id}"
        params = {"optimistic-locking-version": version}
        async with httpx.AsyncClient() as client:
            resp = await client.delete(url, headers=self.headers, params=params)
            if resp.status_code != 204:
                await self.handle_async_response(resp)

    async def create_slo(self, name: str, description: str, criteria: List[Dict],
                         custom_sli: Dict = None, tags: List[str] = None) -> Dict:
        url = f"{self.base_url}{self.slo_api_path}/slos"
        payload = {
            "name": name,
            "description": description,
            "criteria": criteria
        }
        if custom_sli:
            payload["customSli"] = custom_sli
        if tags:
            payload["tags"] = tags

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self.headers, json=payload)
            return await self.handle_async_response(resp)