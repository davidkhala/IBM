import asyncio
import json
import unittest
import uuid

from fastapi.testclient import TestClient
from microsoft_agents.activity import Activity

from src import frames
from src.app import create_app
from src.bridge import Bridge
from src.config import Settings
from src.streaming import StreamingSession
from src.wxo import Delta

ENV = {
    "WXO_USERNAME": "u",
    "WXO_PASSWORD": "p",
    "WXO_AGENT": "a",
    "WS_UPDATE_INTERVAL": "0",
    "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID": "00000000-0000-0000-0000-000000000001",
    "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET": "secret",
    "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID": "00000000-0000-0000-0000-000000000002",
}


class FakeWxo:
    def __init__(self, chunks=("Hel", "lo ", "world"), fail_after: int | None = None):
        self.chunks, self.fail_after, self.calls = chunks, fail_after, []

    async def stream(self, text, thread_id=None):
        self.calls.append((text, thread_id))
        for i, c in enumerate(self.chunks):
            if self.fail_after is not None and i >= self.fail_after:
                raise RuntimeError("boom")
            yield Delta(text=c, thread_id="thread-1")
        yield Delta(done=True)

    async def aclose(self):
        pass


class FakeSocket:
    """扮演 Azure Bot Service 一侧:喂入入站字节,收集出站字节。"""

    def __init__(self):
        self.inbound: asyncio.Queue[bytes | None] = asyncio.Queue()
        self.parser, self.collector = frames.FrameParser(), None
        self.outbound: asyncio.Queue = asyncio.Queue()

    async def receive_bytes(self) -> bytes:
        data = await self.inbound.get()
        if data is None:
            raise ConnectionError("closed")
        return data

    async def send_bytes(self, data: bytes) -> None:
        await self.outbound.put(data)


def request_bytes(verb: str, path: str, body: dict | None = None) -> tuple[uuid.UUID, bytes]:
    req_id, out = uuid.uuid4(), b""
    head = {"verb": verb, "path": path}
    stream = []
    if body is not None:
        data = json.dumps(body).encode()
        sid = uuid.uuid4()
        head["streams"] = [{"id": str(sid), "type": "application/json", "length": len(data)}]
        stream = frames.encode_payload(frames.STREAM, sid, data)
    for h, c in frames.encode_payload(frames.REQUEST, req_id, json.dumps(head).encode()) + stream:
        out += h + c
    return req_id, out


def response_bytes(req_id: uuid.UUID, status: int, body: dict | None = None) -> bytes:
    head = {"statusCode": status}
    stream = []
    if body is not None:
        data = json.dumps(body).encode()
        sid = uuid.uuid4()
        head["streams"] = [{"id": str(sid), "type": "application/json", "length": len(data)}]
        stream = frames.encode_payload(frames.STREAM, sid, data)
    return b"".join(h + c for h, c in frames.encode_payload(frames.RESPONSE, req_id, json.dumps(head).encode()) + stream)


def user_activity(text="hi") -> dict:
    return {
        "type": "message", "id": "act-1", "text": text, "channelId": "directline",
        "serviceUrl": "https://bot.example", "conversation": {"id": "conv-1"},
        "from": {"id": "user"}, "recipient": {"id": "bot"},
    }


async def read_messages(sock: FakeSocket, session_inbox: FakeSocket, count: int, answer_ids=True):
    """读取 count 个出站 Request(并像 Bot Service 一样回 200 + {id}),返回 (path, activity) 列表。"""
    from src.streaming import _Collector
    parser, collector, got = frames.FrameParser(), _Collector(), []
    while len(got) < count:
        data = await asyncio.wait_for(sock.outbound.get(), 5)
        for f in parser.feed(data):
            for m in collector.add(f):
                if m.kind == frames.REQUEST and m.head["verb"] == "POST":
                    got.append((m.head["path"], m.json()))
                    await session_inbox.inbound.put(response_bytes(m.id, 200, {"id": "stream-xyz"}))
                elif m.kind == frames.RESPONSE:
                    got.append(("response", m.head))
    return got


class StreamingSessionTestCase(unittest.IsolatedAsyncioTestCase):
    async def run_session(self, wxo, expect, settings_env=None):
        settings = Settings.from_env({**ENV, **(settings_env or {})})
        sock = FakeSocket()
        session = StreamingSession(sock, Bridge(wxo), settings)
        task = asyncio.create_task(session.run())
        _, data = request_bytes("POST", "/api/messages", user_activity())
        await sock.inbound.put(data)
        got = await read_messages(sock, sock, expect)
        await sock.inbound.put(None)
        with self.assertRaises(ConnectionError):
            await task
        return got

    async def test_streams_partial_updates_then_final(self):
        wxo = FakeWxo()
        got = await self.run_session(wxo, expect=1 + 3 + 1)  # 200 回执 + 3 个 typing + final
        self.assertEqual(got[0], ("response", {"statusCode": 200}))
        posts = [a for p, a in got[1:]]
        paths = [p for p, _ in got[1:]]
        self.assertEqual(paths[0], "/v3/conversations/conv-1/activities/act-1")
        typing, final = posts[:-1], posts[-1]
        self.assertTrue(all(t["type"] == "typing" for t in typing))
        self.assertEqual([t["text"] for t in typing], ["Hel", "Hello ", "Hello world"])
        self.assertEqual([t["entities"][0]["streamSequence"] for t in typing], [1, 2, 3])
        self.assertNotIn("streamId", typing[0]["entities"][0])
        self.assertEqual(typing[1]["entities"][0]["streamId"], "stream-xyz")
        self.assertEqual(final["type"], "message")
        self.assertEqual(final["text"], "Hello world")
        self.assertEqual(final["entities"][0]["streamType"], "final")
        self.assertEqual(final["conversation"]["id"], "conv-1")
        self.assertEqual(wxo.calls, [("hi", None)])

    async def test_no_partial_updates_sends_only_final(self):
        got = await self.run_session(FakeWxo(), expect=2, settings_env={"WS_PARTIAL_UPDATES": "false"})
        self.assertEqual(got[1][1]["type"], "message")
        self.assertEqual(got[1][1]["text"], "Hello world")
        self.assertEqual(got[1][1].get("entities") or [], [])

    async def test_agent_failure_sends_fallback(self):
        got = await self.run_session(FakeWxo(fail_after=0), expect=2)
        self.assertIn("something went wrong", got[1][1]["text"])
        self.assertNotIn("boom", json.dumps(got))

    async def test_version_request(self):
        sock = FakeSocket()
        session = StreamingSession(sock, Bridge(FakeWxo()), Settings.from_env(ENV))
        task = asyncio.create_task(session.run())
        _, data = request_bytes("GET", "/api/version")
        await sock.inbound.put(data)
        got = await read_messages(sock, sock, 1)
        self.assertEqual(got[0], ("response", {"statusCode": 200, "streams": got[0][1]["streams"]}))
        await sock.inbound.put(None)
        with self.assertRaises(ConnectionError):
            await task

    async def test_unknown_path_404(self):
        sock = FakeSocket()
        session = StreamingSession(sock, Bridge(FakeWxo()), Settings.from_env(ENV))
        task = asyncio.create_task(session.run())
        _, data = request_bytes("GET", "/nope")
        await sock.inbound.put(data)
        got = await read_messages(sock, sock, 1)
        self.assertEqual(got[0], ("response", {"statusCode": 404}))
        await sock.inbound.put(None)
        with self.assertRaises(ConnectionError):
            await task


class AppTestCase(unittest.TestCase):
    def test_health_and_auth(self):
        client = TestClient(create_app(ENV, wxo=FakeWxo()))
        self.assertEqual(client.get("/health").json(), {"status": "ok"})
        # 未携带 token 的 HTTP 请求被拒绝
        r = client.post("/api/messages", json=user_activity())
        self.assertEqual(r.status_code, 401)

    def test_websocket_requires_token(self):
        from starlette.websockets import WebSocketDisconnect
        client = TestClient(create_app(ENV, wxo=FakeWxo()))
        with self.assertRaises(WebSocketDisconnect):
            with client.websocket_connect("/api/messages"):
                pass

    def test_websocket_end_to_end_with_anonymous_allowed(self):
        env = {**ENV, "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__ANONYMOUS_ALLOWED": "true"}
        client = TestClient(create_app(env, wxo=FakeWxo(chunks=("ok",))))
        with client.websocket_connect("/api/messages") as ws:
            _, data = request_bytes("POST", "/api/messages", user_activity())
            ws.send_bytes(data)
            from src.streaming import _Collector
            parser, collector, posts, acked = frames.FrameParser(), _Collector(), [], False
            while not posts or posts[-1]["type"] != "message":
                for f in parser.feed(ws.receive_bytes()):
                    for m in collector.add(f):
                        if m.kind == frames.RESPONSE:
                            acked = True
                        else:
                            posts.append(m.json())
                            ws.send_bytes(response_bytes(m.id, 200, {"id": "s1"}))
        self.assertTrue(acked)
        self.assertEqual(posts[-1]["text"], "ok")


if __name__ == "__main__":
    unittest.main()
