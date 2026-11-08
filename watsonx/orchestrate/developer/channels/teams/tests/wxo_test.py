import json
import unittest

import httpx

from src.config import Settings
from src.wxo import WxoClient, parse_sse_line

ENV = {"WXO_USERNAME": "u", "WXO_PASSWORD": "p", "WXO_AGENT": "my_agent"}


def sse(event: str, data: dict) -> str:
    """真实 wxo 的格式:每行一个裸 JSON 事件。"""
    return json.dumps({"id": "1-0", "event": event, "data": data}) + "\n\n"


class ParseSseTestCase(unittest.TestCase):
    def test_delta(self):
        line = sse("message.delta", {"thread_id": "t1", "delta": {"content": [{"text": "Hel"}, {"text": "lo"}]}}).strip()
        d = parse_sse_line(line)
        self.assertEqual((d.text, d.thread_id, d.done), ("Hello", "t1", False))

    def test_standard_sse_prefix_is_accepted(self):
        line = "data: " + sse("message.delta", {"delta": {"content": [{"text": "x"}]}}).strip()
        self.assertEqual(parse_sse_line(line).text, "x")

    def test_completed_and_done(self):
        self.assertTrue(parse_sse_line(sse("message.completed", {}).strip()).done)
        self.assertTrue(parse_sse_line("data: [DONE]").done)

    def test_ignored_lines(self):
        for line in ("", "event: x", "data:", ": keepalive"):
            self.assertIsNone(parse_sse_line(line))

    def test_other_event_carries_thread_id(self):
        d = parse_sse_line(sse("run.started", {"thread_id": "t9"}).strip())
        self.assertEqual((d.text, d.thread_id, d.done), ("", "t9", False))


class WxoClientTestCase(unittest.IsolatedAsyncioTestCase):
    def make(self, handler) -> WxoClient:
        return WxoClient(Settings.from_env(ENV), transport=httpx.MockTransport(handler))

    async def test_login_stream_and_thread(self):
        calls, bodies = [], []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append((request.method, request.url.path, request.url.params.get("tenant_id")))
            path = request.url.path
            if path.endswith("/auth/token"):
                return httpx.Response(200, json={"access_token": "tok-" + (request.url.params.get("tenant_id") or "x"), "token_type": "bearer"})
            if path.endswith("/tenants"):
                return httpx.Response(200, json=[{"id": "T1"}])
            if path.endswith("/orchestrate/agents"):
                self.assertEqual(request.headers["Authorization"], "Bearer tok-T1")
                return httpx.Response(200, json=[{"id": "A1", "name": "my_agent"}])
            if path.endswith("/runs/stream"):
                bodies.append(json.loads(request.content))
                body = sse("message.delta", {"thread_id": "th", "delta": {"content": [{"text": "hi"}]}}) + sse("message.completed", {})
                return httpx.Response(200, content=body.encode(), headers={"content-type": "text/event-stream"})
            return httpx.Response(404)

        client = self.make(handler)
        out = [d async for d in client.stream("hello", "old-thread")]
        await client.aclose()
        self.assertEqual("".join(d.text for d in out), "hi")
        self.assertEqual(bodies[0]["agent_id"], "A1")
        self.assertEqual(bodies[0]["thread_id"], "old-thread")
        self.assertEqual(bodies[0]["message"], {"role": "user", "content": "hello"})

    async def test_relogin_on_401(self):
        state = {"auths": 0, "streams": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path.endswith("/auth/token"):
                state["auths"] += 1
                return httpx.Response(200, json={"access_token": f"tok{state['auths']}", "token_type": "bearer"})
            if path.endswith("/tenants"):
                return httpx.Response(200, json=[{"id": "T1"}])
            if path.endswith("/orchestrate/agents"):
                return httpx.Response(200, json=[{"id": "A1", "name": "my_agent"}])
            if path.endswith("/runs/stream"):
                state["streams"] += 1
                if state["streams"] == 1:
                    return httpx.Response(401)
                return httpx.Response(200, content=sse("message.completed", {}).encode())
            return httpx.Response(404)

        client = self.make(handler)
        out = [d async for d in client.stream("x")]
        await client.aclose()
        self.assertEqual(state["streams"], 2)
        self.assertTrue(out[-1].done)

    async def test_unknown_agent(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/auth/token"):
                return httpx.Response(200, json={"access_token": "t", "token_type": "bearer"})
            if request.url.path.endswith("/tenants"):
                return httpx.Response(200, json=[{"id": "T1"}])
            return httpx.Response(200, json=[])

        client = self.make(handler)
        with self.assertRaises(RuntimeError):
            await client.agent_id()
        await client.aclose()


if __name__ == "__main__":
    unittest.main()
