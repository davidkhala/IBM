# Azure Bot ↔ wxo Developer Edition

把 Azure Bot(Teams 等渠道)收到的消息转发给本地 wxo Developer Edition 的 agent,并把回复流式返回。

同一个 `/api/messages` 路径同时提供两种接入方式:

| Azure Bot 配置 | 协议 | 回复方式 |
| --- | --- | --- |
| Messaging endpoint(默认) | `POST /api/messages` | 用 Microsoft 365 Agents SDK 处理;Teams/WebChat/Direct Line 下以 `typing` 流式更新,最终发 `message` |
| Enable Streaming Endpoint | `WS /api/messages` | 在同一条 WebSocket 上按 Bot Framework Streaming Extensions 帧协议收发;发送 `typing` 增量更新,最终发 `message` |

一个 Azure Bot `conversation.id` 对应一个 wxo thread,多轮对话共享上下文(进程内存,重启后重置)。

## 配置

在项目目录创建 `.env` 并填写。

| 变量 | 说明 |
| --- | --- |
| `WXO_BASE_URL` | 默认 `http://localhost:4321/api/v1` |
| `WXO_USERNAME` / `WXO_PASSWORD` | 可选;默认使用 Developer Edition 内置用户(与 `orchestrate` CLI 相同) |
| `WXO_AGENT` | 必填;要转发到的 agent 名称(`orchestrate agents list`) |
| `WXO_TENANT_ID` | 可选;默认取登录用户可见的第一个 tenant |
| `WS_PARTIAL_UPDATES` | Streaming Endpoint 是否发送增量更新,默认 `true` |
| `WS_UPDATE_INTERVAL` | 增量更新的最小间隔(秒),默认 `0.5` |
| `ENTRA_APP_CLIENT_ID` | Azure Bot 绑定的 Entra ID App Registration 的 Application (client) ID |
| `ENTRA_APP_TENANT_ID` | 该 App Registration 的 Directory (tenant) ID |
| `ENTRA_APP_CLIENT_SECRET` | 该 App Registration 的 Client secret(HTTP Messaging endpoint 回复消息时使用) |

`/api/messages` 默认校验 Azure 签发的 JWT(HTTP 校验 `Authorization` 头,WebSocket 校验升级请求里的 `Authorization` 头),未通过返回 401 / 关闭连接。

## 运行

```powershell
podman rm -f wxo-teams-channel
podman build --network=host -t wxo-teams-channel .
podman run -d --rm --network=host --name wxo-teams-channel --env-file .env -e PORT=3978 wxo-teams-channel
```

端口由运行容器时的 `PORT` 环境变量决定(必填),见 [`Dockerfile`](Dockerfile)。

使用 `--network=host`:容器与 podman machine 共用网络,`localhost:4321` 即本地 wxo Developer Edition,`WXO_BASE_URL` 保持默认值即可;同时避免 netavark 在与 wxo 共用的 WSL2 网络里创建 nftables 规则失败(`nft did not return successfully while applying ruleset`)。host 网络下不需要 `-p` 端口映射。

Message endpoint:`http://127.0.0.1:3978/api/messages`(端口为 `PORT` 的值)。

## 接入 Azure Bot

Azure Bot 需要公网 HTTPS 地址,本地调试可用 ngrok 之类的工具把 `3978` 端口暴露出来。

1. Azure Bot → Configuration → **Messaging endpoint** 填 `https://<公网地址>/api/messages`。
2. 要使用 Streaming Endpoint,在同一页勾选 **Enable Streaming Endpoint**。Bot Service 会改为连接 `wss://<公网地址>/api/messages`,公网入口必须转发 WebSocket 升级请求。
3. Bot 的 App ID、Secret、Tenant ID 填入上表对应的 `ENTRA_APP_*` 变量。

## 测试

```powershell
uv run pytest tests
```

[`tests/wxo_test.py`](tests/wxo_test.py) 直接连接本地运行的 wxo Developer Edition,使用 `.env`(或环境变量)里的 `WXO_*` 配置,`WXO_AGENT` 必须是 wxo 中已存在的 agent。
