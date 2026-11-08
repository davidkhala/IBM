# Azure Bot ↔ wxo Developer Edition

把 Azure Bot(Teams 等渠道)收到的消息转发给本地 wxo Developer Edition 的 agent,并把回复流式返回。

同一个 `/api/messages` 路径同时提供两种接入方式:

| Azure Bot 配置 | 协议 | 回复方式 |
| --- | --- | --- |
| Messaging endpoint(默认) | `POST /api/messages` | 用 Microsoft 365 Agents SDK 处理;Teams/WebChat/Direct Line 下以 `typing` 流式更新,最终发 `message` |
| Enable Streaming Endpoint | `WS /api/messages` | 在同一条 WebSocket 上按 Bot Framework Streaming Extensions 帧协议收发;发送 `typing` 增量更新,最终发 `message` |

一个 Azure Bot `conversation.id` 对应一个 wxo thread,多轮对话共享上下文(进程内存,重启后重置)。

## 配置

复制 [`.env.example`](.env.example) 为 `.env` 并填写。

| 变量 | 说明 |
| --- | --- |
| `WXO_BASE_URL` | 默认 `http://localhost:4321/api/v1` |
| `WXO_USERNAME` / `WXO_PASSWORD` | 本地 wxo 登录用户。Developer Edition 内置用户见 `davidkhala.ibm.watsonx.orchestrate.developer.API.login` |
| `WXO_AGENT` | 要转发到的 agent 名称(`orchestrate agents list`) |
| `WXO_TENANT_ID` | 可选;默认取登录用户可见的第一个 tenant |
| `WS_PARTIAL_UPDATES` | Streaming Endpoint 是否发送增量更新,默认 `true` |
| `WS_UPDATE_INTERVAL` | 增量更新的最小间隔(秒),默认 `0.5` |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID` / `CLIENTSECRET` / `TENANTID` | Azure Bot 的 App Registration |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__ANONYMOUS_ALLOWED` | 仅本地调试时设为 `true`,跳过 JWT 校验 |
| `PORT` | 默认 `3978` |

`/api/messages` 默认校验 Azure 签发的 JWT(HTTP 校验 `Authorization` 头,WebSocket 校验升级请求里的 `Authorization` 头),未通过返回 401 / 关闭连接。

## 运行

```powershell
uv sync
uv run uvicorn main:app --host 127.0.0.1 --port 3978
```

容器方式见 [`Dockerfile`](Dockerfile),默认监听 `0.0.0.0:3978`。

## 接入 Azure Bot

Azure Bot 需要公网 HTTPS 地址,本地调试可用 dev tunnel 之类的工具把 `3978` 端口暴露出来。

1. Azure Bot → Configuration → **Messaging endpoint** 填 `https://<公网地址>/api/messages`。
2. 要使用 Streaming Endpoint,在同一页勾选 **Enable Streaming Endpoint**。Bot Service 会改为连接 `wss://<公网地址>/api/messages`,公网入口必须转发 WebSocket 升级请求。
3. Bot 的 App ID、Secret、Tenant ID 填入上表对应变量。

## 测试

```powershell
uv run pytest tests
```

测试使用 mock 的 wxo,不依赖本地服务。
