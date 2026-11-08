# 02 — 配置

在解压后的发行包目录(`bob/onprem/ibm-bob/`)内操作。需要准备三类配置:

| 文件 | 必需 | 用途 |
| ---- | ---- | ---- |
| `config.yaml` | 是 | 命名空间、存储类、镜像仓库、add-on、模型密钥 |
| `model-gateway.yaml` | 建议 | LLM 端点定义;缺省则 Bob 无模型可用 |
| `my-idp.yaml` | 否 | LDAP/AD 联邦,安装后通过 `bobctl configure-idp` 应用 |

## 2.1 config.yaml

```bash
cp config-template.yaml config.yaml
```

### global

| 字段 | 默认值 | 说明 |
| ---- | ------ | ---- |
| `operatorNamespace` | `ibm-bob-operators` | 由 `bobctl` 自动创建,**勿手工创建** |
| `instanceNamespace` | `ibm-bob` | 由 `bobctl` 自动创建,**勿手工创建** |
| `fileStorageClass` | 集群默认 | RWX 存储类,如 `ocs-storagecluster-cephfs` |
| `blockStorageClass` | 集群默认 | RWO 存储类,如 `ocs-storagecluster-ceph-rbd` |
| `imagePullPrefix` | `icr.io` | 镜像前缀;air-gapped 填私有仓库主机名 |
| `imagePullSecretName` | `ibm-entitlement-key` | 由 `bobctl install --registry-creds` 创建 |

示例(connected + ODF):

```yaml
global:
  operatorNamespace: ibm-bob-operators
  instanceNamespace: ibm-bob
  fileStorageClass: ocs-storagecluster-cephfs
  blockStorageClass: ocs-storagecluster-ceph-rbd
  imagePullPrefix: icr.io
  imagePullSecretName: ibm-entitlement-key
```

### bob(add-on,Bob Core 无需开启)

| 字段 | 默认 | 说明 |
| ---- | ---- | ---- |
| `rag.enabled` | false | Z Premium Package(RAG),自动包含 OpenSearch |
| `zProxy.enabled` | false | Z Premium Package(Proxy),需要 `rag.enabled: true` |
| `understand.enabled` | false | Z Understand and Refactor |

> 开启 add-on 会显著增加资源占用(Core + Z Context + Z Understand 约 35.8 vCPU / 84.8 GiB / ~55 GiB PV),开启前先核对容量。

`config.yaml` 不含证书设置,TLS 在安装后用 `bobctl setup-route` 配置。

## 2.2 模型网关

完整说明见官方 [Configuring the Model Gateway](https://bob.ibm.com/docs/ide/enterprise/on-premises/model-gateway/configuration)。

规则:

- `models` 中必须包含三个保留名称:`premium-ide`(交互聊天默认模型)、`security`(guardrail)、`background`(后台任务)。
- 同一时刻只能配置一个核心推理模型,多个会导致未定义行为。
- `routers` 固定为 `name: router`、`strategy: static`、`default_model: premium-ide`。
- 密钥通过 `env.<VAR>` 引用,变量值写在 `config.yaml` 的 `bob.modelGateway.secrets` 下。
- `supports_vision` 仅在模型确实支持图像时设为 `true`;Nemotron 3、Laguna S2.1 须为 `false`。

### 方案 A — 自建 vLLM / RHOAI(OpenAI 兼容)

`model-gateway.yaml`:

```yaml
x-providers:
  inference_service: &isvc
    openai_compatible:
      model: nvidia/nemotron-3-ultra-550b
      base_url: https://<llm-inference-server>
      api_key: env.INFERENCE_API_KEY
    model_info:
      exposed: true
      provider: nvidia
      family: nemotron
      version: "3-ultra"
      max_input_tokens: 262144
      supports_vision: false
      mode: chat

models:
  - &chat_llm
    <<: *isvc
    model_name: premium-ide
  - <<: *chat_llm
    model_name: security
  - <<: *chat_llm
    model_name: background

routers:
  - name: router
    strategy: static
    static:
      default_model: premium-ide
```

`config.yaml` 对应片段:

```yaml
bob:
  modelGateway:
    secrets:
      INFERENCE_API_KEY: "<api-key>"
```

> `security` / `background` 建议改用更小的模型(如 `openai/gpt-oss-20b`)时,为它们单独写 `openai_compatible` 条目,不要沿用 `chat_llm` 锚点。

### 方案 B — AWS Bedrock

`model-gateway.yaml` 的 provider 段:

```yaml
bedrock:
  model: us.anthropic.claude-sonnet-5
  region: us-east-1
  access_key_id: env.AWS_ACCESS_KEY
  secret_access_key: env.AWS_SECRET_ACCESS_KEY
```

`config.yaml`:`bob.modelGateway.secrets.AWS_ACCESS_KEY` / `AWS_SECRET_ACCESS_KEY`。

### 方案 C — Azure OpenAI / Google Vertex

- Azure:`openai_compatible` + `base_url: https://<resource>.cognitiveservices.azure.com/openai` + `api_key: env.AZURE_API_KEY`
- Vertex:`vertex` + `project` / `location` + `credentials: env.GEMINI_CREDENTIALS`(**base64** 编码的 service-account JSON)

### 私有 CA 的模型端点

端点使用自签/企业 CA 时,二选一:

1. **推荐**:安装后给 CA Secret 打标签,Operator 自动并入信任包,无需重启:

   ```bash
   oc create secret generic my-model-endpoint-ca --from-file=tls.crt=model-ca.crt -n $INSTANCE_NS
   oc label secret my-model-endpoint-ca bob.ibm.com/inferencing-bundle-ca=true -n $INSTANCE_NS
   ```

2. 单模型 `ca_cert_pem: env.CA_CERT`,并在 `config.yaml` 的 `bob.modelGateway.secrets.CA_CERT` 中粘贴完整 PEM。

## 2.3 IDP(可选,可延后)

```bash
cp config-idp-template.yaml my-idp.yaml
```

填写邮箱域名、管理员邮箱以及可选的 LDAP/AD 连接、搜索与用户映射。`bobctl install` 不需要此文件,安装后再应用,见 [05-post-install.md](./05-post-install.md)。

## 2.4 配置检查清单

- [ ] `config.yaml` 的两个存储类名称与 `oc get storageclass` 一致
- [ ] `global.imagePullPrefix` 与安装方式匹配(connected 为 `icr.io`)
- [ ] `model-gateway.yaml` 含 `premium-ide` / `security` / `background` 三项和 `router`
- [ ] 所有 `env.<VAR>` 在 `bob.modelGateway.secrets` 中都有对应值
- [ ] 未把 `config.yaml`、`model-gateway.yaml` 提交到 git
