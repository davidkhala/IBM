# watsonx Orchestrate Developer Edition
<https://developer.watson-orchestrate.ibm.com/developer_edition/wxOde_overview>

Hardware requirements

- 8-core, 16GB
- `--with-doc-processing`: 8-core, 24GB

include *watsonx Orchestrate server* and *watsonx Orchestrate UI*

## watsonx Orchestrate server

port：4321

- optional service: Langfuse
- OpenAPI Docs
  - exposed in `<host>/docs`
  - published in <https://developer.watson-orchestrate.ibm.com/developer_edition/api_authentication>

## watsonx Orchestrate UI

port: 3000

## Provision

```
orchestrate server start -e .env --accept-terms-and-conditions --service-password An75Lovh^Ky^oP55mN
```

- 安装过程中可能会因网络问题go build minio的途中失败。
  - 请将dnsTunneling=true和autoProxy=true，加入`~\.wslconfig`

Trace

- `Set Master Password for Local Services`:
  - > Password must be a minimum of 18 characters. Password must contain only letters, numbers and allowed symbols. Whitespace is not permitted
  - specified by `--service-password` to avoid interactive prompt

- `[INFO] - No existing distro found — creating new WSL distro named ibm-watsonx-orchestrate...`
  - It will create a WSL, which takes time.
- [INFO] - You can run `orchestrate env activate local` to set your environment or `orchestrate chat start` to start the UI service and begin chatting
  - Indicator of process complete
- `orchestrate chat start` will start on http://localhost:3000/chat-lite