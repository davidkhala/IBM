# 02 — 配置

需要准备三类配置:

| 文件 | 必需 | 用途 |
| ---- | ---- | ---- |
| `config.yaml` | 是 | 命名空间、存储类、镜像仓库、add-on、模型密钥 |
| `config-model-gateway.yaml` | 是 | LLM 端点定义;缺省则 Bob 无模型可用 |
| `config-idp.yaml` | 否 | LDAP/AD 联邦,安装后通过 `admin.sh configureIdp` 应用 |

## 2.1 config.yaml

- config.yaml 不含证书设置。安装时使用默认自签证书;如需企业/私有 CA 证书,请在安装后按 05-post-install.md 配置。

### global

| 字段 | 默认值 | 说明 |
| ---- | ------ | ---- |
| `fileStorageClass` | 集群默认 | RWX 存储类,如 `ocs-storagecluster-cephfs` |
| `blockStorageClass` | 集群默认 | RWO 存储类,如 `ocs-storagecluster-ceph-rbd` |
| `imagePullPrefix` | `icr.io` | 镜像前缀 |


## 2.2 模型网关

完整说明见官方 [Configuring the Model Gateway](https://bob.ibm.com/docs/ide/enterprise/on-premises/model-gateway/configuration)。

规则:

- `models` 中必须包含三个保留名称:`premium-ide`(交互聊天默认模型)、`security`(guardrail)、`background`(后台任务)。
- 密钥通过 `env.<VAR>` 引用,变量值写在 `config.yaml` 的 `bob.modelGateway.secrets` 下。
- `supports_vision` 仅在模型确实支持图像时设为 `true`。

> `security` / `background` 建议改用更小的模型(如 `openai/gpt-oss-20b`)时,为它们单独写 `x-providers` 条目,不要沿用 `chat_llm` 锚点。


### 方案 A — AWS Bedrock

`model-gateway.yaml` 的 provider 段:

```yaml
bedrock:
  model: us.anthropic.claude-sonnet-5
  region: us-east-1
  access_key_id: env.AWS_ACCESS_KEY
  secret_access_key: env.AWS_SECRET_ACCESS_KEY
```

`config.yaml`:`bob.modelGateway.secrets.AWS_ACCESS_KEY` / `AWS_SECRET_ACCESS_KEY`。

### 方案 B — Azure OpenAI / Google Vertex

- Azure:`base_url: https://<resource>.cognitiveservices.azure.com/openai` + `api_key: env.AZURE_API_KEY`
- Vertex: `project` + `credentials: env.GEMINI_CREDENTIALS`(**base64** 编码的 service-account JSON)
