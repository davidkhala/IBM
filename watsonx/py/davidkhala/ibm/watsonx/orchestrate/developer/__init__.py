from davidkhala.utils.http_request import Request


class API(Request):
    def __init__(self, protocol: str = 'http', host: str = 'localhost', port: str | int = 4321) -> None:
        self.base_url = f"{protocol}://{host}:{port}/api/v1"
        self.tenant_id: str
        super().__init__()

    def login(self, username: str = "wxo.archer@ibm.com", password: str = "watsonx",
              tenant_id: str | None = None):
        """
        Two-step token flow. On success, the tenant-scoped token is applied as bearer to all later requests.

        The defaults are the built-in local user hardcoded in the `orchestrate` CLI
        (`ibm_watsonx_orchestrate_clients.common.service_instance.local_service_instance.DEFAULT_USER`).
        They are NOT the `--service-username`/`--service-password` of `orchestrate server start`,
        which only secure Langfuse, Minio, MCP Gateway, etc.
        :param username: login user of the local wxo-server
        :param password: login password of the local wxo-server
        :param tenant_id: default to the first tenant visible to the user
        """

        self.options["headers"].pop("Authorization", None)

        if tenant_id is None:
            self.set_bearer(self._auth(username, password))
            tenant_id = self.tenant()
        self.tenant_id = tenant_id
        self.set_bearer(self._auth(username, password, tenant_id))

    def _auth(self, username: str, password: str, tenant_id: str | None = None):
        r = self.request(f"{self.base_url}/auth/token", "POST",
                         params={"tenant_id": tenant_id},
                         data={"username": username, "password": password}
                         )
        return r["access_token"]

    def tenant(self):
        r = self.tenants()
        assert len(r) == 1
        assert r[0]["name"] == "wxo-dev"
        assert r[0]["title"] == "WatsonX Orchestrate Development"
        return r[0]["id"]

    def tenants(self):
        """login required"""
        return self.request(f"{self.base_url}/tenants", "GET")
