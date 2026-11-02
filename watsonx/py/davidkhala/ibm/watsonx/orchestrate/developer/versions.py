from requests import HTTPError

from davidkhala.ibm.watsonx.orchestrate.developer import API


class A2A(API):
    @property
    def client(self):
        r = self.request(f"{self.base_url}/a2a/versions", "GET", params={"role": "client"})

        return r['current_version']

    @property
    def server(self):
        """A2A server role not yet implemented"""
        try:
            self.request(f"{self.base_url}/a2a/versions", "GET", params={"role": "server"})
        except HTTPError as err:
            if not (
                    err.response.status_code == 501 and
                    err.response.text == """{"detail":"A2A server role is not yet implemented"}"""
            ):
                raise
