from os import PathLike
from typing import Iterator, Union

from ibm_botocore.exceptions import ClientError
from ibm_botocore.response import StreamingBody
from urllib3 import HTTPResponse
from davidkhala.ibm.cloud.object import Client, WithBucket


class Object(WithBucket):
    def __init__(self, client: Client, bucket: str, key: str):
        super().__init__(client, bucket)
        self.key = key

    def upload(self, file: PathLike):
        self._.upload_file(file, self.bucket, self.key)

    def download(self, file: Union[str, PathLike]):
        self._.download_file(self.bucket, self.key, str(file))

    def read_stream(self, chunk_size=StreamingBody._DEFAULT_CHUNK_SIZE) -> Iterator[bytes]:
        response = self._.get_object(Bucket=self.bucket, Key=self.key)
        return response["Body"].iter_chunks(chunk_size=chunk_size)

    def delete_if_exists(self) -> bool:
        try:
            self._.head_object(Bucket=self.bucket, Key=self.key)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
        self.delete()
        return True

    def delete(self):
        self._.delete_object(Bucket=self.bucket, Key=self.key)

    def write_stream(self, stream: HTTPResponse, part_size=5 * 1024 * 1024):
        mpu = self._.create_multipart_upload(Bucket=self.bucket, Key=self.key)
        upload_id = mpu["UploadId"]

        parts = []
        part_number = 1
        try:
            while True:
                chunk = stream.read(part_size)
                if not chunk:
                    break
                part = self._.upload_part(
                    Bucket=self.bucket,
                    Key=self.key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=chunk
                )
                parts.append({"ETag": part["ETag"], "PartNumber": part_number})
                part_number += 1

            if not parts:
                self._.put_object(Bucket=self.bucket, Key=self.key, Body=b"")
            else:
                self._.complete_multipart_upload(
                    Bucket=self.bucket, Key=self.key,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts}
                )
        except Exception:
            self._.abort_multipart_upload(
                Bucket=self.bucket, Key=self.key, UploadId=upload_id
            )
            raise
