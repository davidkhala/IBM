# 01 — 前置条件
- 支持的 OCP 版本:4.20 / 4.21 / 4.22。

## Hardware requirement
- Bob Core 请求约 10.8 vCPU / 10.8 GiB / ~24 GiB PV;
- Insufficient storage throughput or I/O performance, particularly for PostgreSQL workloads, can result in increased response times, slower indexing operations, and degraded overall system performance. 

### 官方参考拓扑

来源 [Minimum reference configuration
](https://bob.ibm.com/docs/ide/enterprise/on-premises/system-requirements#minimum-reference-configuration)

| Node role |	Count	| CPU per node | Memory per node | Storage | 	
| Control plane | 3	| 4 vCPU (minimum)|	16 GiB (minimum)|	50 GiB |
| Infrastructure nodes | 	3	|~4 vCPU	|~16 GiB	| 50 GiB |
| Worker nodes | 	3	| 8 vCPU |	16 GiB	| 200 GiB |

### crc参考规格
12 CPU, 32 GiB, 100  GiB


## cli dependencies
工作站工具校验:

```bash
./preinstall.sh binCheck

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

- 在ROKS on IBM CLoud的环境上，如果在IBM Cloud 的Cluster 的Overview控制面，`Networking` section > `Outbound traffic protection enabled`是provision 的设置。则会由于`disableAllDefaultSources: true`导致访问不了catalog source
  - solution:`oc patch operatorhub cluster --type merge -p '{"spec":{"disableAllDefaultSources":false}}'`


校验:

```bash
./admin.sh certmanStatus
```
### GUI install
在*Ecosystem > Software Catalog*下安装 **cert-manager Operator for Red Hat OpenShift**
- channel 选 `stable-v1`


### cli install
```
./admin.sh installCertman
```

## 1.7 准备 LLM 端点

Bob 需要两类托管模型端点(模型本身不在 Bob 安装范围):

- **核心推理模型**
- **Guardrail 模型**:如 `openai/gpt-oss-20b`

支持的 provider:AWS Bedrock、Azure OpenAI、Google Vertex。详见 [02-configuration.md](./02-configuration.md)。

## 1.8 DNS 与证书策略(提前决定)

- Bob 应用 endpoint 需要 DNS 记录,客户端须能访问 ingress。
- 决定使用企业/公共 CA 证书,还是默认自签 CA(`CN=Bob Internal CA`)。`bob-ide` / `bob-shell` 在证书未被信任前无法连接。证书在安装**之后**通过 `bobctl setup-route` 应用,详见 [05-post-install.md](./05-post-install.md)。

## 检查清单
- [ ] 已确定证书策略与 DNS 方案
