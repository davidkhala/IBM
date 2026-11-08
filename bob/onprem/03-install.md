# 03 — 安装

所有命令在 WSL 的 `bob/onprem/ibm-bob/` 目录下执行。

## 3.0 选择安装方式

| 方面 | Connected | Air-gapped(直接镜像) | Air-gapped(间接镜像) |
| ---- | --------- | --------------------- | --------------------- |
| 镜像来源 | 集群直接从 IBM Container Registry 拉取 | 镜像到内部仓库 | 镜像到内部仓库 |
| 适用 | 集群可访问 `icr.io` | 工作站可同时访问 IBM 与私有仓库 | 联网环境与隔离环境分离 |
| 模型推理 | 托管或本地 | 仅本地 | 仅本地 |
| 遥测 | 默认开启(可关闭) | 关闭 | 关闭 |

本环境已登录 `cp.icr.io`,按 **Connected** 执行(3.1)。Air-gapped 见 3.5。

## 3.1 安装前确认

```bash
oc whoami && oc whoami --show-server     # 确认是目标集群的 cluster-admin
oc get crd | grep cert-manager.io        # cert-manager 已就绪
test -f config.yaml && echo "config.yaml OK"
test -n "$IBM_ENTITLEMENT_KEY" && echo "key set"
```

(`IBM_ENTITLEMENT_KEY` 通过 WSLENV 从 PowerShell 传入,见 [01-prerequisites.md](./01-prerequisites.md) 1.1。)

## 3.2 生成并应用集群级资源

```bash
./bobctl generate-cluster-resources
```

产物:`work/cluster-resources.yaml`,仅含 `ibm-bob-cluster-scoped/` 中的 CRD、ClusterRole、ClusterRoleBinding 等。**应用前请管理员或安全团队审阅。**

```bash
less work/cluster-resources.yaml
oc apply -f work/cluster-resources.yaml --force-conflicts --server-side
```

## 3.3 预演(可选,推荐)

```bash
./bobctl install \
  --registry-creds "cp:${IBM_ENTITLEMENT_KEY}" \
  --accept-license \
  --model-config ./model-gateway.yaml \
  --dry-run
```

## 3.4 执行安装

```bash
./bobctl install \
  --registry-creds "cp:${IBM_ENTITLEMENT_KEY}" \
  --accept-license \
  --model-config ./model-gateway.yaml
```

| 参数 | 必需 | 说明 |
| ---- | ---- | ---- |
| `--registry-creds <user:password>` | 是 | Connected 场景为 `cp:<entitlement key>`;仅当私有仓库无需认证时可省略 |
| `--accept-license` | 是 | 不带则不会继续 |
| `--model-config <file>` | 否 | 省略则 Bob 无模型,需安装后 `bobctl update-model-config` |
| `--dry-run` | 否 | 只显示计划变更 |

> 注意:`$IBM_ENTITLEMENT_KEY` 展开会进入 shell 历史/进程参数,仅在受控的个人工作站执行,执行后可 `history -c`。

`bobctl` 会创建 Operator 与 Instance 两个命名空间并部署全部组件,完成后进入 [04-verify.md](./04-verify.md)。

## 3.5 Air-gapped 方式

均需先完成 `config.yaml` 中 `global.imagePullPrefix` 指向私有仓库主机名。

### 直接镜像(工作站可同时访问两端)

```bash
./bobctl mirror-images \
  --dest-registry <your-registry> \
  --src-creds "cp:${IBM_ENTITLEMENT_KEY}" \
  --dest-creds <user:password> \
  --arch amd64

./bobctl verify-images --creds <user:password> --arch amd64
```

### 间接镜像(经离线介质)

联网工作站:

```bash
./bobctl download-images \
  --to-dir /path/to/images \
  --src-creds "cp:${IBM_ENTITLEMENT_KEY}" \
  --arch amd64
```

将 `/path/to/images` 与 `work/` 目录(含 `*-from-filesystem-mapping.lst`)带入隔离环境,`work/` 放在 `bobctl` 根目录下(或设置 `BOB_WORK_DIR`):

```bash
./bobctl upload-images \
  --from-dir /path/to/images \
  --dest-registry <your-registry> \
  --dest-creds <user:password>

./bobctl verify-images --creds <user:password> --arch amd64
```

### 之后(两种 air-gapped 通用)

```bash
./bobctl generate-cluster-resources
oc apply -f work/cluster-resources.yaml --force-conflicts --server-side
./bobctl install --registry-creds <user:password> --accept-license --model-config ./model-gateway.yaml
```

`verify-images` 读取 `global.imagePullPrefix`,不能对 `icr.io` 使用。

## 3.6 安装后添加/更新模型配置

安装时未带 `--model-config`,或需要切换模型时:

```bash
./bobctl update-model-config --model-config ./model-gateway.yaml --update-secrets --dry-run
./bobctl update-model-config --model-config ./model-gateway.yaml --update-secrets
```

| 参数 | 作用 |
| ---- | ---- |
| `--model-config <file>` | 更新 ConfigMap `bob-inference-model-config` |
| `--update-secrets` | 用 `config.yaml` 的 `bob.modelGateway.secrets` 更新 Secret `bob-inference-model-secrets` |

至少提供其中一个。
