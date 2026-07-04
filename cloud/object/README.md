> Bucket with objects cannot be deleted.
- > The bucket name will be available again 15 minutes after bucket deletion.
- Ref to [Empty a bucket](https://cloud.ibm.com/docs/cloud-object-storage?topic=cloud-object-storage-deleting-multiple-objects-patterns)


IBM COS 没法做流输入
- 不接受没有 Content-Length 的单次 PUT
- 在发送 PUT 请求前，会强制调用 seek(0)
- Solution: 只能用multipart_upload
