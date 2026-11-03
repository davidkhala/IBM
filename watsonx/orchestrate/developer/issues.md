# Limit

Setup Microsoft Teams integration

- Developer Edition 是跑在localhost的。而 Teams 这类渠道的 channel 会生成一个 event URL 接收来自 Teams（Azure Bot Service）的消息回调. Microsoft 的 Bot Framework 需要一个公网可访问的 HTTPS endpoint，本地的 localhost 无法满足


```
Exception in thread Thread-15 (_readerthread):
UnicodeDecodeError: 'gbk' codec can't decode byte 0xa4 in position 2: illegal multibyte sequence
```

- root cause: 在 Windows 系统下，Python 默认使用 GBK 编码去读取某些以 UTF-8（或其他非 GBK 编码）格式保存的文件或输出流时引起的。
- 无法修复


安装过程中可能会因网络问题go build minio的途中失败。
- for windows: 请将`dnsTunneling=true`和`autoProxy=true`，加入`~\.wslconfig`


# Documentation mismatch

API 登录凭证与 `--service-username` / `--service-password` 无关

- 官方文档 `developer_edition/api_authentication` 称：`POST /api/v1/auth/token` 的 `username` / `password` 是启动时 `orchestrate server start` 配置的 `--service-username` 和 `--service-password`
- 实测：使用 `--service-username`（如 `david`）、默认的 `orchestrate` 均登录失败
- root cause: `--service-username` / `--service-password` 只作用于 Langfuse、Minio、MCP Gateway、ClickHouse 等周边服务（见 `~/.cache/orchestrate/merged.env` 中的 `LANGFUSE_USERNAME`、`MINIO_ROOT_USER`、`MCP_GATEWAY_BASIC_USER`）。`orchestrate` CLI 访问 wxo-server 时使用的是写死在 `ibm_watsonx_orchestrate_clients/common/service_instance/local_service_instance.py` 中的 `DEFAULT_USER`
  - username: `wxo.archer@ibm.com`
  - password: `watsonx`
- 租户：CLI 取 `name == "wxo-dev"` 的租户，不存在则创建
- 登录流程（已验证）：`POST /api/v1/auth/token` → `GET /api/v1/tenants` → `POST /api/v1/auth/token?tenant_id=<id>`，之后以租户级 token 作为 Bearer
- 实现见 [`API.login`](../../py/davidkhala/ibm/watsonx/orchestrate/developer/__init__.py)
