from davidkhala.ibm.watsonx.orchestrate.developer import API


class Agents:
    def __init__(self, api: API) -> None:
        self.api = api
        self.base_url = f"{api.base_url}/orchestrate/agents"

    def list(self) -> list | dict:
        return self.api.request(self.base_url, "GET")

    @staticmethod
    def prettier(agent: dict) -> dict:
        """Drop `description` and audit fields; turn `environments` into a dict keyed by `draft`/`live`."""
        dropped = {"description", "created_by", "updated_by", "created_on", "updated_at"}
        result = {k: v for k, v in agent.items() if k not in dropped}
        result["environments"] = {
            env["name"]: {k: v for k, v in env.items() if k != "name"}
            for env in agent.get("environments", [])
        }
        return result
