from __future__ import annotations

import asyncio
import httpx


class HubAdminClient:
    """Async client for the hub admin API used by the Discord bot."""

    def __init__(self, base_url: str, token: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    async def close(self):
        await self._client.aclose()

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    async def enqueue_command(self, node_id: str, action: str, instance: str, params: dict | None = None) -> dict:
        payload = {
            "node_id": node_id,
            "action": action,
            "instance": instance,
            "params": params,
        }
        resp = await self._client.post("/api/commands", headers=self._headers(), json=payload)
        resp.raise_for_status()
        return resp.json()["command"]

    async def list_commands(self, node_id: str | None = None) -> list[dict]:
        params = {"node_id": node_id} if node_id else None
        resp = await self._client.get("/api/commands", headers=self._headers(), params=params)
        resp.raise_for_status()
        return resp.json()["commands"]

    async def list_logs(self, node_id: str | None = None, command_id: str | None = None) -> list[dict]:
        params = {}
        if node_id:
            params["node_id"] = node_id
        if command_id:
            params["command_id"] = command_id
        resp = await self._client.get("/api/logs", headers=self._headers(), params=params or None)
        resp.raise_for_status()
        return resp.json()["logs"]

    async def download_log(self, log_id: str) -> tuple[str, bytes]:
        resp = await self._client.get(f"/api/logs/{log_id}", headers=self._headers())
        resp.raise_for_status()
        filename = self._extract_filename(resp)
        if not filename:
            filename = f"{log_id}.log"
        return filename, resp.content

    async def wait_for_log(self, command_id: str, timeout: float = 60.0, poll_interval: float = 3.0) -> dict | None:
        elapsed = 0.0
        while elapsed < timeout:
            logs = await self.list_logs(command_id=command_id)
            if logs:
                return logs[0]
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        return None

    @staticmethod
    def _extract_filename(resp: httpx.Response) -> str | None:
        disposition = resp.headers.get("content-disposition")
        if not disposition:
            return None
        parts = disposition.split(";")
        for part in parts:
            if "filename=" in part:
                value = part.split("=", 1)[1].strip()
                return value.strip('"')
        return None
