import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from .config import Settings


@dataclass
class Delta:
    """一次流式事件的结果。text 为增量文本;thread_id 为 wxo 会话线程。"""
    text: str = ""
    thread_id: str | None = None
    done: bool = False


class WxoClient:
    """wxo Developer Edition 客户端:登录 -> 解析 agent -> 调用 runs/stream(SSE)。"""

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self._http = httpx.AsyncClient(
            base_url=settings.wxo_base_url.rstrip("/"),
            timeout=httpx.Timeout(10.0, read=120.0),
            transport=transport,
        )
        self._token: str | None = None
        self._agent_id: str | None = None

    async def aclose(self):
        await self._http.aclose()

    async def _auth(self, tenant_id: str | None = None) -> str:
        r = await self._http.post(
            "/auth/token",
            params={"tenant_id": tenant_id} if tenant_id else None,
            data={"username": self.settings.wxo_username, "password": self.settings.wxo_password},
        )
        r.raise_for_status()
        return r.json()["access_token"]

    async def login(self):
        """两步登录:先取无租户 token,再换取租户 token。"""
        tenant_id = self.settings.wxo_tenant_id
        if tenant_id is None:
            r = await self._http.get("/tenants", headers={"Authorization": f"Bearer {await self._auth()}"})
            r.raise_for_status()
            tenants = r.json()
            if not tenants:
                raise RuntimeError("wxo returned no tenant for this user")
            tenant_id = tenants[0]["id"]
        self._token = await self._auth(tenant_id)
        self._agent_id = None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """带一次 token 过期重登录的请求。"""
        if self._token is None:
            await self.login()
        r = await self._http.request(method, url, headers=self._headers(), **kwargs)
        if r.status_code == 401:
            await self.login()
            r = await self._http.request(method, url, headers=self._headers(), **kwargs)
        r.raise_for_status()
        return r

    async def agent_id(self) -> str:
        if self._agent_id is None:
            r = await self._request("GET", "/orchestrate/agents", params={"names": self.settings.wxo_agent})
            agents = [a for a in r.json() if a.get("name") == self.settings.wxo_agent]
            if not agents:
                raise RuntimeError(f"wxo agent not found: {self.settings.wxo_agent}")
            self._agent_id = agents[0]["id"]
        return self._agent_id

    async def stream(self, text: str, thread_id: str | None = None) -> AsyncIterator[Delta]:
        body = {
            "agent_id": await self.agent_id(),
            "message": {"role": "user", "content": text},
        }
        if thread_id:
            body["thread_id"] = thread_id

        for attempt in (0, 1):
            if self._token is None:
                await self.login()
            async with self._http.stream(
                "POST", "/orchestrate/runs/stream", headers=self._headers(), json=body
            ) as r:
                if r.status_code == 401 and attempt == 0:
                    await self.login()
                    continue
                r.raise_for_status()
                async for line in r.aiter_lines():
                    delta = parse_sse_line(line)
                    if delta is None:
                        continue
                    yield delta
                    if delta.done:
                        return
                return


def parse_sse_line(line: str) -> Delta | None:
    """解析流中的一行。wxo 每行是一个裸 JSON 事件;也兼容标准 SSE 的 ``data:`` 前缀。
    空行、注释行、其他 SSE 字段返回 None。"""
    payload = line.removeprefix("data:").strip()
    if not payload.startswith("{") and payload != "[DONE]":
        return None
    if payload == "[DONE]":
        return Delta(done=True)
    event = json.loads(payload)
    data = event.get("data") or {}
    kind = event.get("event")
    thread_id = data.get("thread_id")

    if kind == "message.delta":
        text = "".join(c.get("text", "") for c in (data.get("delta") or {}).get("content") or [])
        return Delta(text=text, thread_id=thread_id)
    if kind in ("message.completed", "done"):
        return Delta(thread_id=thread_id, done=True)
    if thread_id:
        return Delta(thread_id=thread_id)
    return None
