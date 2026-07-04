from os import PathLike

from urllib3 import HTTPResponse

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

    def write_stream(self, stream: HTTPResponse, part_size=5 * 1024 * 1024):
        mpu = self.client.client.create_multipart_upload(Bucket=self.bucket, Key=self.key)
        upload_id = mpu["UploadId"]

        parts = []
        part_number = 1
        while True:
            chunk = stream.read(part_size)
            if not chunk:
                break
            part = self.client.client.upload_part(
                Bucket=self.bucket,
                Key=self.key,
                PartNumber=part_number,
                UploadId=upload_id,
                Body=chunk
            )
            parts.append({"ETag": part["ETag"], "PartNumber": part_number})
            part_number += 1
        self.client.client.complete_multipart_upload(
            Bucket=self.bucket, Key=self.key,
            UploadId=upload_id,
            MultipartUpload={"Parts": parts}
        )
