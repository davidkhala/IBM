import unittest

from davidkhala.ibm.watsonx.orchestrate.developer import API
from davidkhala.ibm.watsonx.orchestrate.developer.channel import Teams


class TeamsTest(unittest.TestCase):
    """Requires a running Developer Edition server with at least one agent.

    Credentials come from environment variables: TEAMS_APP_ID, TEAMS_APP_PASSWORD, TEAMS_TENANT_ID (optional)
    """

    @classmethod
    def setUpClass(cls):
        cls.client_id = "50e96ffd-da34-4029-9bd5-669366c741a6"  # Application (client) ID
        cls.client_secret = ""  # client secret
        cls.tenant_id = "c2a38aca-e9c7-4647-8dcd-9185476159ae"
        if not (cls.client_id and cls.client_secret):
            raise unittest.SkipTest("TEAMS_APP_ID and TEAMS_APP_PASSWORD are required")

        cls.api = API()
        agents = cls.api.request(f"{cls.api.base_url}/orchestrate/agents", "GET")
        agent = next((a for a in agents if a.get("environments")), None)
        if agent is None:
            raise unittest.SkipTest("No agent with environment found")
        environment = next(
            (e for e in agent["environments"] if e["name"] == "draft"),
            agent["environments"][0],
        )
        cls.teams = Teams(cls.api, agent["id"], environment["id"])

    def test_lifecycle(self):
        created = self.teams.create(
            self.client_id,
            self.client_secret,
            teams_tenant_id=self.tenant_id,
            name="test_teams_channel",
            description="created by test_channel.py",
        )
        print(created)
        channel_id = created["id"]
        try:
            self.assertEqual(channel_id, self.teams.get(channel_id)["id"])
            self.assertIn(channel_id, [c["id"] for c in self.teams.list()])

            updated = self.teams.update(channel_id, enable_feedback=True)
            print(updated)
            self.assertTrue(self.teams.get(channel_id)["enable_feedback"])
        finally:
            self.teams.delete(channel_id)

        self.assertNotIn(channel_id, [c["id"] for c in self.teams.list()])


if __name__ == "__main__":
    unittest.main()
