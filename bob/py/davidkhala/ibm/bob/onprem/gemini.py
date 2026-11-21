import base64
import json

from davidkhala.gcp.auth.service_account import from_service_account
from google.genai import Client


def from_service_account_info(encoded: str) -> Client:
    info = base64.b64decode(encoded).decode("utf-8")
    account = from_service_account(json.loads(info))
    return Client(
        enterprise=True,
        credentials=account.credentials,
        project=account.project,
    )
