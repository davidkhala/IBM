import os
import unittest
from pathlib import Path

from davidkhala.ibm.cloud.object import Client


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        api_key = os.environ.get("API_KEY")
        resource_instance_id = "crn:v1:bluemix:public:cloud-object-storage:global:a/d3c4213fe445f1da20087df4b56f2637:69379df5-c781-4935-a843-6efbdf5ad9e7::"
        region = 'ca-tor'
        self.client = Client(api_key, resource_instance_id, region)


from davidkhala.ibm.cloud.object.object import Object


class UploadTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.bucket = 'f3eb0b6b-96e4-482f-9cc7-a033fb6a0f77'

    def test_upload(self):
        o = Object(self.client, self.bucket, 'temp/uv.lock')
        file = Path(__file__).parent.parent / 'uv.lock'
        o.upload(file)

    def test_write_stream(self):
        import io
        empty_stream = io.BytesIO(b"")
        o = Object(self.client, self.bucket, 'empty.stream')
        o.write_stream(empty_stream)


from davidkhala.ibm.cloud.object.bucket import Bucket


class BucketTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self._ = Bucket(self.client, 'f3eb0b6b-96e4-482f-9cc7-a033fb6a0f77')

    def test_buckets(self):
        buckets = self._.buckets
        for bucket in buckets:
            print(bucket.Name)

    def test_nuke(self):
        bucket = "masterdatamanagement-donotdelete-pr-wllwyejsw9vhrp"
        b = Bucket(self.client, bucket)
        b.nuke()
