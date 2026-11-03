import unittest


class GetTest(unittest.TestCase):

    def test_A2A(self):
        from davidkhala.ibm.watsonx.orchestrate.developer.versions import A2A
        c = A2A()
        print(c.server)
        self.assertEqual("0.3.0", c.client)

class LoginTest(unittest.TestCase):

    def setUp(self) -> None:
        from davidkhala.ibm.watsonx.orchestrate.developer import API
        self.api = API()
        self.api.login("wxo.archer@ibm.com", "watsonx")

    def test_agents(self):
        from davidkhala.ibm.watsonx.orchestrate.developer.agents import Agents
        c = Agents(self.api)
        agents = c.list()
        self.assertGreater(len(agents), 0)
        print(agents[0])


if __name__ == "__main__":
    unittest.main()
