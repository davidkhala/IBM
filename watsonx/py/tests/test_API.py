import unittest


class GetTest(unittest.TestCase):

    def test_A2A(self):
        from davidkhala.ibm.watsonx.orchestrate.developer.versions import A2A
        c = A2A()
        print(c.server)
        self.assertEqual("0.3.0", c.client)


if __name__ == "__main__":
    unittest.main()
