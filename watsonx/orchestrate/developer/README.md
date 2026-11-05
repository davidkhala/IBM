# watsonx Orchestrate Developer Edition
<https://developer.watson-orchestrate.ibm.com/developer_edition/wxOde_overview>

Hardware requirements

- 8-core, 16GB
- `--with-doc-processing`: 8-core, 24GB

include *watsonx Orchestrate server* and *watsonx Orchestrate UI*

Prebuilt agent
- `DocProcessing`
- `AskOrchestrate`

## watsonx Orchestrate server

port：4321
- get actual port usage by `orchestrate env list`

optional service: Langfuse

API
- API Base URL: `http://localhost:4321/api/v1`
- OpenAPI Docs: `http://localhost:4321/docs`
  - published in <https://developer.watson-orchestrate.ibm.com/developer_edition/api_authentication>

## watsonx Orchestrate UI

port: 3000

It also support provision via [container compose](./container/)

## Provision

```
orchestrate server start -e .env --accept-terms-and-conditions --service-password An75Lovh^Ky^oP55mN
```
- dependency list
  - redis
  - minio
  - milvus
  - etcd
  - clickhouse
  - langfuse
  - langflow
  - pg (wxo-server-db)



Trace

- `Set Master Password for Local Services`:
  - > Password must be a minimum of 18 characters. Password must contain only letters, numbers and allowed symbols. Whitespace is not permitted
  - specified by `--service-password` to avoid interactive prompt

- `[INFO] - No existing distro found — creating new WSL distro named ibm-watsonx-orchestrate...`
  - It will create a WSL, which takes time.
- [INFO] - You can run `orchestrate env activate local` to set your environment or `orchestrate chat start` to start the UI service and begin chatting
  - Indicator of process complete
- `orchestrate chat start` will start on http://localhost:3000/chat-lite
  - The command will hang if `orchestrate server start` does not run yet even if `orchestrate env` is ready

## Resume
`orchestrate server start -e .env`