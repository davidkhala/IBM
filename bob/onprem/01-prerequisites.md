# 01 — 前置条件


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
| `oc` | 与集群版本一致或相差一个小版本(最低 OCP 4.20) | OpenShift CLI |
| `helm` | ≥ 3.14.0 | `bobctl` 部署时调用 |
| `bash` | ≥ 3.2 | 运行 `bobctl` |
| `openssl` | ≥ 3.5(或系统自带) | `get-ca-cert`、`setup-route`、`reset-route` 使用 |


## 1.1 IBM Entitled Registry 登录

Bob 后端镜像位于 IBM Entitled Container Registry(`cp.icr.io`,部分镜像在 `icr.io`),发行包不含镜像。

entitlement key 获取:登录 [My IBM Container software library](https://myibm.ibm.com/products-services/containerlibrary) → **Active entitlement keys** → [Add new key]/[Copy]


```
podman login -u cp cp.icr.io # interactive password input
podman login --get-login cp.icr.io          # 期望输出: cp
```

> 说明:`podman login` 只证明 key 有效、本机可访问 `cp.icr.io`。安装时 `bobctl install` 需要单独传入 `--registry-creds cp:<key>` 来在集群内创建镜像拉取 Secret(默认名 `ibm-entitlement-key`?),**不会**读取 podman 的登录状态。

`global.imagePullPrefix` 默认为 `icr.io`,建议同时验证该域名，注意这里使用的是IBM Cloud API key:

```
podman login -u iamapikey icr.io # interactive password input, using IBM Cloud API key
podman login --get-login icr.io  # 期望输出: iamapikey
```


## 1.3 下载并解压发行包

从 [IBM Bob GitHub 仓库](https://github.com/IBM/ibm-bob) 的 Release 下载 `ibm-bob-install-<version>.tar.gz`,放到本目录(`bob/onprem/`)后:

发行包结构:

```
|- /bin
|- /charts
|- /etc
|- logs
README.md
bobctl
...
```

## 1.4 集群访问与权限

需要 `cluster-admin`(或等价 RBAC)。

```bash
oc login <api-server> --token=<cluster-admin-token>
oc whoami # kubeadmin
oc whoami --show-server # https://api.crc.testing:6443
oc get clusterversion        # VERSION 须为 4.20 / 4.21 / 4.22
```

确认当前上下文就是目标集群后再继续。

## 1.5 集群容量与存储

```bash
oc get storageclass
```

支持的存储Supported storage classes
- OpenShift Data Foundation (ODF)
- Managed NFS

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

- [ ] `podman login --get-login cp.icr.io` 返回 `cp`
- [ ] `oc` / `helm` / `bash` / `openssl` 版本满足要求
- [ ] 发行包已解压,`./bobctl --help` 正常
- [ ] `oc whoami` 为 cluster-admin,`oc get clusterversion` 为 4.20–4.22
- [ ] 已确认 RWX / RWO 存储类名称
- [ ] cert-manager ≥ v1.14 运行正常
- [ ] 核心模型与 guardrail 模型端点已就绪且集群可达
- [ ] 已确定证书策略与 DNS 方案
