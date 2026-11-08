import logging
from collections.abc import Mapping
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from microsoft_agents.activity import load_configuration_from_env
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.core.authorization.jwt import _authorize_request
from microsoft_agents.hosting.core.http import HttpResponse
from microsoft_agents.hosting.fastapi import CloudAdapter, jwt_authorization_decorator, start_agent_process

from .agent import build_agent
from .bridge import Bridge
from .config import Settings, to_sdk_env
from .streaming import StreamingSession
from .wxo import WxoClient

logger = logging.getLogger(__name__)


class _WebSocketAdapter:
    def __init__(self, ws: WebSocket):
        self._ws = ws

    async def receive_bytes(self) -> bytes:
        message = await self._ws.receive()
        if message["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(message.get("code", 1000))
        return message.get("bytes") or (message.get("text") or "").encode()

    async def send_bytes(self, data: bytes) -> None:
        await self._ws.send_bytes(data)


def create_app(env: Mapping[str, str], wxo: WxoClient | None = None) -> FastAPI:
    settings = Settings.from_env(env)
    sdk_config = load_configuration_from_env(to_sdk_env(env))
    connection_manager = MsalConnectionManager(**sdk_config)
    wxo = wxo or WxoClient(settings)
    bridge = Bridge(wxo)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        await wxo.aclose()

    app = FastAPI(lifespan=lifespan)
    app.state.agent_configuration = connection_manager.get_default_connection_configuration()
    adapter = CloudAdapter(connection_manager=connection_manager)
    agent = build_agent(connection_manager, bridge)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("unhandled error")
        return JSONResponse(status_code=502, content={"detail": "Bad gateway"})

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/api/messages")
    @jwt_authorization_decorator
    async def messages(request: Request):
        return await start_agent_process(request, agent, adapter)

    @app.websocket("/api/messages")
    async def streaming_messages(websocket: WebSocket):
        # Azure Bot Service 在 WebSocket 升级请求里携带 Bearer token
        result = await _authorize_request(websocket.headers.get("Authorization"), app.state.agent_configuration)
        if isinstance(result, HttpResponse):
            await websocket.close(code=1008)
            return
        await websocket.accept()
        session = StreamingSession(_WebSocketAdapter(websocket), bridge, settings)
        try:
            await session.run()
        except WebSocketDisconnect:
            pass
        except Exception:
            logger.exception("streaming session failed")
            await websocket.close(code=1011)

    return app
