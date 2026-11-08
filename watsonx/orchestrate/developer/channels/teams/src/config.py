from collections.abc import Mapping
from dataclasses import dataclass

# wxo Developer Edition 内置的本地用户(orchestrate CLI 使用的同一个)
DEFAULT_USERNAME = "wxo.archer@ibm.com"
DEFAULT_PASSWORD = "watsonx"

# 对外的环境变量名 -> Microsoft 365 Agents SDK 约定的配置键(SDK 按 "__" 拆分层级)
_SDK_ENV_KEYS = {
    "ENTRA_APP_CLIENT_ID": "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID",
    "ENTRA_APP_CLIENT_SECRET": "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET",
    "ENTRA_APP_TENANT_ID": "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID",
}


def to_sdk_env(env: Mapping[str, str]) -> dict[str, str]:
    """把 ENTRA_APP_* 环境变量翻译成 SDK 需要的键,其余变量原样保留。"""
    return {**env, **{sdk: env[name] for name, sdk in _SDK_ENV_KEYS.items() if env.get(name)}}


@dataclass(frozen=True)
class Settings:
    wxo_base_url: str
    wxo_username: str
    wxo_password: str
    wxo_agent: str
    wxo_tenant_id: str | None = None
    ws_partial_updates: bool = True
    ws_update_interval: float = 0.5

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "Settings":
        if not env.get("WXO_AGENT"):
            raise ValueError("missing required environment variables: WXO_AGENT")
        return cls(
            wxo_base_url=env.get("WXO_BASE_URL") or "http://localhost:4321/api/v1",
            wxo_username=env.get("WXO_USERNAME") or DEFAULT_USERNAME,
            wxo_password=env.get("WXO_PASSWORD") or DEFAULT_PASSWORD,
            wxo_agent=env["WXO_AGENT"],
            wxo_tenant_id=env.get("WXO_TENANT_ID") or None,
            ws_partial_updates=(env.get("WS_PARTIAL_UPDATES") or "true").lower() in ("1", "true", "yes"),
            ws_update_interval=float(env.get("WS_UPDATE_INTERVAL") or 0.5),
        )
