# 01 — 前置条件
- 支持的 OCP 版本:4.20 / 4.21 / 4.22。


## Hardware requirement
- Bob Core 请求约 10.8 vCPU / 10.8 GiB / ~24 GiB PV;参考拓扑为 3 个 worker(各 8 vCPU / 16 GiB / 200 GiB)。
- [Minimum reference configuration
](https://bob.ibm.com/docs/ide/enterprise/on-premises/system-requirements#minimum-reference-configuration)


| Node role |	Count	| CPU per node | Memory per node |	
| Control plane | 3	| 4 vCPU (minimum)|	16 GiB (minimum)|	
| Infrastructure nodes | 	3	|~4 vCPU	|~16 GiB	|
| Worker nodes | 	3	| 8 vCPU |	16 GiB	|

Storage I/O
- Insufficient storage throughput or I/O performance, particularly for PostgreSQL workloads, can result in increased response times, slower indexing operations, and degraded overall system performance. 


## cli dependencies
工作站工具(Linux)
| 工具 | 要求 | 说明 |
| ---- | ---- | ---- |
| `bobctl` | 发行包内 `./bobctl` | 安装、配置、管理 Bob |
| `oc` | 与集群版本一致或相差一个小版本(最低 OCP 4.20) | OpenShift CLI |
| `helm` | ≥ 3.14.0 | `bobctl` 部署时调用 |
| `bash` | ≥ 3.2 | 运行 `bobctl` |
| `openssl` | ≥ 3.5(或系统自带) | `get-ca-cert`、`setup-route`、`reset-route` 使用 |

安装 `oc` 与 `helm` 请参考官方下载页(使用对应版本的 tar 包解压到 `PATH`):

- OpenShift CLI:集群 Web Console 右上角 **? → Command line tools**
- Helm:<https://helm.sh/docs/intro/install/>

校验:

```bash
oc version
helm version
bash --version
openssl version
```

## 1.3 下载并解压发行包

从 [IBM Bob GitHub 仓库](https://github.com/IBM/ibm-bob) 的 Release 下载 `ibm-bob-install-<version>.tar.gz`,放到本目录(`bob/onprem/`)后:

发行包结构:

| 目录 | 范围 | 内容 |
| ---- | ---- | ---- |
| `?ibm-bob-cluster-scoped/` | 集群级 | CRD、ClusterRole、ClusterRoleBinding,需管理员审核 |
| `ibm-bob/` | 命名空间级 | Operator、命名空间 RBAC、ServiceAccount、Bob 工作负载 |

后续 runbook 中的 `./bobctl`、`config.yaml`、`config-template.yaml` 均指该解压目录。

## 1.4 集群访问与权限

需要 `cluster-admin`(或等价 RBAC)。

```bash
oc login <api-server> --token=<cluster-admin-token>
oc whoami # kubeadmin
oc whoami --show-server # https://api.crc.testing:6443
oc get clusterversion   # VERSION 须为 4.20 / 4.21 / 4.22
```

确认当前上下文就是目标集群后再继续。

## 1.5 集群容量与存储

```bash
oc get storageclass
```

支持的存储Supported storage classes
- `ocs-storagecluster-cephfs`: OpenShift Data Foundation (ODF)
- `managed-nfs-storage`: Managed NFS

## 1.6 安装 cert-manager(v1.14+)

`bobctl install` 启动时会检查 cert-manager CRD,缺失则立即中止。

推荐方式:OperatorHub(aka. Software Catalog) 安装 **cert-manager Operator for Red Hat OpenShift**,channel 选 `stable-v1`

校验:

```bash
oc get pods -n cert-manager                 # 控制器 Pod 均为 Running
oc get crd certificates.cert-manager.io issuers.cert-manager.io clusterissuers.cert-manager.io certificaterequests.cert-manager.io           # 核心 CRD 存在检查
```

## 1.7 准备 LLM 端点

Bob 需要两类模型端点(模型本身的部署不在 Bob 安装范围):

- **核心推理模型**:如 Nvidia Nemotron 3 Ultra
- **Guardrail 模型**:如 `openai/gpt-oss-20b`

支持的 provider 形式:`openai_compatible`(Azure OpenAI、vLLM、RHOAI 等)、`bedrock`、`vertex`。详见 [02-configuration.md](./02-configuration.md)。

从集群内验证网络可达(把 `<base_url>` 换成实际端点):

```bash
oc run net-test --rm -it --restart=Never --image=registry.access.redhat.com/ubi9/ubi-minimal -- \
  curl -sS -o /dev/null -w '%{http_code}\n' --max-time 10 <base_url>
```

任何 HTTP 状态码(含 401/404)均表示网络连通;超时或 DNS 失败需先处理防火墙、代理、NetworkPolicy。

## 1.8 DNS 与证书策略(提前决定)

- Bob 应用 endpoint 需要 DNS 记录,客户端须能访问 ingress。
- 决定使用企业/公共 CA 证书,还是默认自签 CA(`CN=Bob Internal CA`)。`bob-ide` / `bob-shell` 在证书未被信任前无法连接。证书在安装**之后**通过 `bobctl setup-route` 应用,详见 [05-post-install.md](./05-post-install.md)。

## 检查清单

- [ ] 核心模型与 guardrail 模型端点已就绪且集群可达
- [ ] 已确定证书策略与 DNS 方案
