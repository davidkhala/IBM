import unittest

from davidkhala.ibm.watsonx.orchestrate.developer import API
from davidkhala.ibm.watsonx.orchestrate.developer.agents import Agents
from davidkhala.ibm.watsonx.orchestrate.developer.channel import Teams


class TeamsTest(unittest.TestCase):
    """Requires a running Developer Edition server with at least one agent.

    Credentials come from environment variables: TEAMS_APP_ID, TEAMS_APP_PASSWORD, TEAMS_TENANT_ID (optional)
    """

    @classmethod
    def setUpClass(cls):
        cls.api = API()
        cls.api.login()
        agents = Agents(cls.api).list()
        agent = Agents.prettier(agents[0])
        environment = agent['environments']['draft']

        cls.client_id = "50e96ffd-da34-4029-9bd5-669366c741a6"  # Application (client) ID
        cls.client_secret = "--"  # client secret
        cls.tenant_id = "c2a38aca-e9c7-4647-8dcd-9185476159ae"
        if not (cls.client_id and cls.client_secret):
            raise unittest.SkipTest("TEAMS_APP_ID and TEAMS_APP_PASSWORD are required")

        cls.teams = Teams(cls.api, agent["id"], environment["id"])

    def test_list(self):
        print(self.teams.list())

    def test_lifecycle(self):
        created = self.teams.create(
            self.client_id,
            self.client_secret,
            teams_tenant_id=self.tenant_id,
            name="test_teams_channel",
        )
        print(created)


        self.assertEqual(created, self.teams.get(created)["id"])
        self.assertIn(created, [c["id"] for c in self.teams.list()])

        updated = self.teams.update(created, enable_feedback=False)
        print(updated)
        self.assertFalse(self.teams.get(created)["enable_feedback"])
        self.teams.delete(created)

        self.assertNotIn(created, [c["id"] for c in self.teams.list()])


if __name__ == "__main__":
    unittest.main()
