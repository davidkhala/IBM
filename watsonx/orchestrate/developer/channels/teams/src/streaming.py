"""Azure Bot "Enable Streaming Endpoint":Bot Service 通过 WebSocket 连接到 /api/messages,
双方在同一条连接上以 Request/Response/Stream 帧互发 HTTP 风格的请求。

- 入站:Bot Service 发来 ``POST /api/messages``(负载为 Activity),本端立即回 200,再异步处理
- 出站:本端向 Bot Service 发 ``POST /v3/conversations/{id}/activities[/{replyToId}]`` 回复 Activity
"""
import asyncio
import contextlib
import logging
import uuid
from typing import Protocol

from microsoft_agents.activity import Activity

from . import frames
from .bridge import Bridge
from .config import Settings

logger = logging.getLogger(__name__)

JSON_TYPE = "application/json; charset=utf-8"
REQUEST_TIMEOUT = 30.0
FALLBACK_TEXT = "Sorry, something went wrong while contacting the agent."


class Socket(Protocol):
    async def receive_bytes(self) -> bytes: ...

    async def send_bytes(self, data: bytes) -> None: ...


class Message:
    """一个已收齐 Stream 的 Request 或 Response。"""

    def __init__(self, kind: str, id_: uuid.UUID, head: dict, bodies: list[bytes]):
        self.kind, self.id, self.head, self.bodies = kind, id_, head, bodies

    def json(self):
        import json
        return json.loads(self.bodies[0]) if self.bodies and self.bodies[0] else None


class _Collector:
    """把 A/B 帧和它声明的 S 帧配对。S 帧可能先于或晚于 A/B 帧到达。"""

    MAX_PENDING = 256

    def __init__(self):
        self._heads: dict[tuple[str, uuid.UUID], tuple[dict, list[uuid.UUID]]] = {}
        self._streams: dict[uuid.UUID, bytes] = {}

    def add(self, frame: frames.Frame) -> list[Message]:
        import json
        if frame.type in (frames.REQUEST, frames.RESPONSE):
            head = json.loads(frame.payload or b"{}")
            ids = [uuid.UUID(s["id"]) for s in head.get("streams") or []]
            self._heads[(frame.type, frame.id)] = (head, ids)
        elif frame.type == frames.STREAM:
            self._streams[frame.id] = frame.payload
        if len(self._heads) > self.MAX_PENDING or len(self._streams) > self.MAX_PENDING:
            raise ValueError("too many incomplete messages")

        done = []
        for key, (head, ids) in list(self._heads.items()):
            if all(i in self._streams for i in ids):
                del self._heads[key]
                done.append(Message(key[0], key[1], head, [self._streams.pop(i) for i in ids]))
        return done


class StreamingSession:
    def __init__(self, socket: Socket, bridge: Bridge, settings: Settings):
        self.socket = socket
        self.bridge = bridge
        self.settings = settings
        self._pending: dict[uuid.UUID, asyncio.Future[Message]] = {}
        self._tasks: set[asyncio.Task] = set()
        self._send_lock = asyncio.Lock()

    async def run(self):
        parser, collector = frames.FrameParser(), _Collector()
        try:
            while True:
                data = await self.socket.receive_bytes()
                for frame in parser.feed(data):
                    for message in collector.add(frame):
                        self._dispatch(message)
        finally:
            for task in self._tasks:
                task.cancel()
            for fut in self._pending.values():
                if not fut.done():
                    fut.cancel()

    def _spawn(self, coro):
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def _dispatch(self, message: Message):
        if message.kind == frames.RESPONSE:
            fut = self._pending.pop(message.id, None)
            if fut and not fut.done():
                fut.set_result(message)
        else:
            self._spawn(self._on_request(message))

    # ---- 发送 ----
    async def _send(self, type_: str, id_: uuid.UUID, payload: bytes):
        async with self._send_lock:
            for header, chunk in frames.encode_payload(type_, id_, payload):
                await self.socket.send_bytes(header + chunk)

    async def _send_with_body(self, type_: str, id_: uuid.UUID, head: dict, body: dict | None):
        if body is not None:
            data = frames.json_bytes(body)
            stream_id = uuid.uuid4()
            head = {**head, "streams": [{"id": str(stream_id), "type": JSON_TYPE, "length": len(data)}]}
            async with self._send_lock:
                for h, c in frames.encode_payload(type_, id_, frames.json_bytes(head)):
                    await self.socket.send_bytes(h + c)
                for h, c in frames.encode_payload(frames.STREAM, stream_id, data):
                    await self.socket.send_bytes(h + c)
        else:
            await self._send(type_, id_, frames.json_bytes(head))

    async def request(self, verb: str, path: str, body: dict) -> Message:
        req_id = uuid.uuid4()
        fut: asyncio.Future[Message] = asyncio.get_running_loop().create_future()
        self._pending[req_id] = fut
        try:
            await self._send_with_body(frames.REQUEST, req_id, {"verb": verb, "path": path}, body)
            return await asyncio.wait_for(fut, REQUEST_TIMEOUT)
        finally:
            self._pending.pop(req_id, None)

    async def _respond(self, req_id: uuid.UUID, status: int, body: dict | None = None):
        await self._send_with_body(frames.RESPONSE, req_id, {"statusCode": status}, body)

    # ---- 入站请求 ----
    async def _on_request(self, message: Message):
        verb, path = message.head.get("verb"), message.head.get("path")
        try:
            if verb == "GET" and path == "/api/version":
                await self._respond(message.id, 200, {"userAgent": "wxo-azure-bot-bridge"})
            elif verb == "POST":
                activity = Activity.model_validate(message.json())
                if activity.type == "invoke":
                    await self._respond(message.id, 501)
                    return
                await self._respond(message.id, 200)
                await self._answer(activity)
            else:
                await self._respond(message.id, 404)
        except Exception:
            logger.exception("failed to handle streaming request")
            with contextlib.suppress(Exception):
                await self._respond(message.id, 500)

    # ---- 回复 ----
    def _reply_path(self, activity: Activity) -> str:
        path = f"/v3/conversations/{activity.conversation.id}/activities"
        return f"{path}/{activity.id}" if activity.id else path

    async def _post_activity(self, activity: Activity, body: dict) -> str | None:
        """发送一个出站 Activity,返回 Bot Service 分配的 id。"""
        response = await self.request("POST", self._reply_path(activity), body)
        if response.head.get("statusCode") != 200:
            raise RuntimeError(f"channel rejected activity: status {response.head.get('statusCode')}")
        result = response.json() or {}
        return result.get("id")

    async def _answer(self, activity: Activity):
        if activity.type != "message" or not activity.conversation:
            return
        text = activity.text or ""
        if activity.recipient:
            text = activity.remove_mention_text(activity.recipient.id) or ""
        text = text.strip()
        if not text:
            return

        base = activity.create_reply().model_dump(mode="json", by_alias=True, exclude_none=True)
        base.pop("id", None)
        loop = asyncio.get_running_loop()
        accumulated, stream_id, sequence, last_sent = "", None, 0, 0.0

        try:
            async for chunk in self.bridge.ask(activity.conversation.id, text):
                accumulated += chunk
                if not self.settings.ws_partial_updates:
                    continue
                if loop.time() - last_sent < self.settings.ws_update_interval:
                    continue
                sequence += 1
                info = {"type": "streaminfo", "streamType": "streaming", "streamSequence": sequence}
                update = {**base, "type": "typing", "text": accumulated, "entities": [info]}
                if stream_id:
                    info["streamId"] = stream_id
                    update["id"] = stream_id
                assigned = await self._post_activity(activity, update)
                stream_id = stream_id or assigned
                last_sent = loop.time()
        except Exception:
            logger.exception("agent call failed")
            accumulated = accumulated or FALLBACK_TEXT

        final = {**base, "type": "message", "text": accumulated or "(no response)"}
        if stream_id:
            final["id"] = stream_id
            final["entities"] = [{"type": "streaminfo", "streamType": "final", "streamId": stream_id}]
        await self._post_activity(activity, final)
