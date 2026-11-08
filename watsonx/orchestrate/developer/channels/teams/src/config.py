from collections.abc import Mapping
from dataclasses import dataclass


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
        missing = [k for k in ("WXO_USERNAME", "WXO_PASSWORD", "WXO_AGENT") if not env.get(k)]
        if missing:
            raise ValueError(f"missing required environment variables: {', '.join(missing)}")
        return cls(
            wxo_base_url=env.get("WXO_BASE_URL") or "http://localhost:4321/api/v1",
            wxo_username=env["WXO_USERNAME"],
            wxo_password=env["WXO_PASSWORD"],
            wxo_agent=env["WXO_AGENT"],
            wxo_tenant_id=env.get("WXO_TENANT_ID") or None,
            ws_partial_updates=(env.get("WS_PARTIAL_UPDATES") or "true").lower() in ("1", "true", "yes"),
            ws_update_interval=float(env.get("WS_UPDATE_INTERVAL") or 0.5),
        )
