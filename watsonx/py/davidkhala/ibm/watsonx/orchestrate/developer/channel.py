from davidkhala.ibm.watsonx.orchestrate.developer import API


class Teams:
    def __init__(self, api: API, agent_id: str, environment_id: str) -> None:
        self.api = api
        self.base_url = f"{api.base_url}/orchestrate/agents/{agent_id}/environments/{environment_id}/channels/teams"

    def create(self, client_id: str, client_secret: str, *,
               teams_tenant_id: str | None = None,
               name: str | None = None,
               **kwargs
               ) -> dict:
        """
        :param client_id: Application (client) ID of the Azure App registration, sent as `app_id`
        :param client_secret: client secret value of the Azure App registration, sent as `app_password`
        TODO: check whether teams_tenant_id can be ignored.
        """
        body = {
            "app_id": client_id,
            "app_password": client_secret,
            "teams_tenant_id": teams_tenant_id,
            "name": name,
            "enable_feedback": True,
            **kwargs
        }
        return self.api.request(self.base_url, "POST", json={k: v for k, v in body.items() if v is not None})

    def list(self) -> list | dict:
        return self.api.request(self.base_url, "GET")

    def get(self, channel_id: str) -> dict:
        return self.api.request(f"{self.base_url}/{channel_id}", "GET")

    def update(self, channel_id: str, *,
               client_id: str | None = None,
               client_secret: str | None = None,
               teams_tenant_id: str | None = None,
               name: str | None = None,
               description: str | None = None,
               enable_feedback: bool | None = None,
               ) -> dict:
        body = {
            "app_id": client_id,
            "app_password": client_secret,
            "teams_tenant_id": teams_tenant_id,
            "name": name,
            "description": description,
            "enable_feedback": enable_feedback,
        }
        return self.api.request(f"{self.base_url}/{channel_id}", "PATCH",
                                json={k: v for k, v in body.items() if v is not None})

    def delete(self, channel_id: str) -> None:
        """Server responds 204 without body"""
        self.api.request(f"{self.base_url}/{channel_id}", "DELETE")
