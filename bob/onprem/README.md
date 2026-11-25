# IBM Bob Self-hosted on OpenShift — Runbook

在 Red Hat OpenShift Container Platform (OCP) 上安装 IBM Bob self-hosted 的操作手册,依据 [IBM Bob 官方文档](https://bob.ibm.com/docs/ide/enterprise/on-premises/installation) 整理。

## 执行顺序

1. [prerequisites](./docs/01-prerequisites.md)
2. [configuration.md](./docs/02-configuration.md)
3. [install.md](./docs/03-install.md)
4. [post-install.md](./docs/04-post-install.md)

每个阶段必须完成后才能进入下一阶段。

## 架构要点



## 敏感信息
- `config.yaml`(含模型密钥)、`model-gateway.yaml`、TLS 私钥、解压后的发行包均已在本目录 [.gitignore](./.gitignore) 中排除,不得提交到版本控制。
