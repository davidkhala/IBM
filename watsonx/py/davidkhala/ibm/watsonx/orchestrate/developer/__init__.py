from davidkhala.utils.http_request import Request


class API(Request):
    def __init__(self, protocol: str = 'http', host: str = 'localhost', port: str | int = 4321 ) -> None:

        self.base_url = f"{protocol}://{host}:{port}/api/v1"
        super().__init__()
