# IBM Bob Self-hosted on OpenShift — Runbook

在 Red Hat OpenShift Container Platform (OCP) 上安装 IBM Bob self-hosted 的操作手册,依据 [IBM Bob 官方文档](https://bob.ibm.com/docs/ide/enterprise/on-premises/installation) 整理。安装通过发行包中的 `bobctl` 完成。

## 执行顺序

| 步骤 | Runbook | 内容 |
| ---- | ------- | ---- |
| 1 | [01-prerequisites.md](./01-prerequisites.md) | 工作站工具、发行包、权限、entitlement key、cert-manager、LLM |
| 2 | [02-configuration.md](./02-configuration.md) | `config.yaml`、`model-gateway.yaml`、IDP 配置 |
| 3 | [03-install.md](./03-install.md) | 集群级资源、`bobctl install`(connected / air-gapped) |
| 4 | [04-verify.md](./04-verify.md) | 安装验证与常见故障排查 |
| 5 | [05-post-install.md](./05-post-install.md) | TLS 证书、IDP/LDAP、用户、下发 endpoint |
| 6 | [06-uninstall.md](./06-uninstall.md) | 卸载 |

每个阶段必须完成后才能进入下一阶段。

## 架构要点

- 两个命名空间:Operator namespace(默认 `ibm-bob-operators`)与 Instance namespace(默认 `ibm-bob`),均由 `bobctl` 自动创建,**不要手工创建**。
- 两步部署:先由 cluster-admin 应用集群级资源(CRD、ClusterRole 等),再运行 `bobctl install`(仅在两个命名空间内操作)。
- 支持的 OCP 版本:4.20 / 4.21 / 4.22。
- Bob Core 最小规模:约 10.8 vCPU / 10.8 GiB 内存 / 约 24 GiB PV(请求值,另需约 25% 调度余量)。
- 推理模型(LLM)不包含在安装内,需要自行准备。

## 工作站环境(Windows)

`bobctl` 是 bash 脚本,依赖 `bash`、`oc`、`helm`、`openssl`。本机 Windows 上 `podman` 可用,`oc`、`helm`、`openssl` 未安装;**除 `podman login` 外的所有命令均在 WSL(Linux)中执行**。

文档中的代码块约定:

- ```` ```powershell ```` — 在 Windows PowerShell 中执行
- ```` ```bash ```` — 在 WSL / Linux bash 中执行

## 约定变量

下列变量贯穿所有 runbook,按需在 bash 会话中设置:

```bash
export OPERATOR_NS=ibm-bob-operators   # 与 config.yaml 的 global.operatorNamespace 一致
export INSTANCE_NS=ibm-bob             # 与 config.yaml 的 global.instanceNamespace 一致
```

## 敏感信息

- entitlement key 只通过环境变量 `IBM_ENTITLEMENT_KEY` 传递,不要写入任何文件。
- `config.yaml`(含模型密钥)、`model-gateway.yaml`、TLS 私钥、解压后的发行包均已在本目录 [.gitignore](./.gitignore) 中排除,不得提交到版本控制。
