from ibm_boto3 import client
from ibm_botocore.client import Config


class Client:
    def __init__(self, api_key: str, resource_instance_id: str, region: str):
        """
        :param api_key: IBM Cloud API key
        :param service_instance_id:
        """
        self.client = client(
            "s3",  # Valid service names are: s3
            ibm_api_key_id=api_key,
            ibm_service_instance_id=resource_instance_id,
            config=Config(signature_version="oauth"),
            endpoint_url=f"https://s3.{region}.cloud-object-storage.appdomain.cloud"
        )
