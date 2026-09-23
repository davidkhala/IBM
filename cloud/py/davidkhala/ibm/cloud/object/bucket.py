import re
from datetime import datetime

from pydantic import BaseModel

from davidkhala.ibm.cloud.object import Client
from davidkhala.ibm.cloud.object.object import Object


class BucketModel(BaseModel):
    Name: str
    CreationDate: datetime


class Bucket:
    def __init__(self, client: Client, bucket: str):
        self._ = client.client
        self.bucket = bucket

    @property
    def buckets(self) -> list[BucketModel]:
        # there is no way to inspect each bucket region?
        return [BucketModel.model_validate(_) for _ in self._.list_buckets()['Buckets']]

    def list_objects(self):
        files = self._.list_objects(Bucket=self.bucket)

        return [file["Key"] for file in files.get('Contents', [])]

    def delete_matching(self, pattern: str | re.Pattern) -> list[str]:
        """Delete all objects whose key matches *pattern*. Returns the list of deleted keys."""
        compiled = re.compile(pattern) if isinstance(pattern, str) else pattern
        deleted = []
        for key in self.list_objects():
            if compiled.search(key):
                Object(self._, self.bucket, key).delete()
                deleted.append(key)
        return deleted

    def nuke(self):
        if not self.exists(): return
        for item_name in self.list_objects():
            o = Object(self._, self.bucket, item_name)
            o.delete()
        self._.delete_bucket(Bucket=self.bucket)

    def exists(self) -> bool:
        try:
            self._.head_bucket(Bucket=self.bucket)
            return True
        except self._.exceptions.NoSuchBucket:
            return False
        except self._.exceptions.ClientError as e:
            # 403 Forbidden → bucket exist but no permission to access
            if e.response["ResponseMetadata"]["HTTPStatusCode"] == 403:
                return True
            return False
