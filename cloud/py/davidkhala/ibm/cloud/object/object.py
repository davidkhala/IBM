from os import PathLike

from davidkhala.ibm.cloud.object import Client


class Object:
    def __init__(self, client: Client, bucket: str, key: str):
        self.client = client
        self.bucket = bucket
        self.key = key

    def upload(self, file: PathLike):
        self.client.client.upload_file(file, self.bucket, self.key)

    def delete(self):
        self.client.client.delete_object(Bucket=self.bucket, Key=self.key)
