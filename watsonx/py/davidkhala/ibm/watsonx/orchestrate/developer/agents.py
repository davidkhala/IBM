from davidkhala.ibm.watsonx.orchestrate.developer import API


class Agents:
    def __init__(self, api: API) -> None:
        self.api = api
        self.base_url = f"{api.base_url}/orchestrate/agents"

    def list(self) -> list | dict:
        return self.api.request(self.base_url, "GET")
