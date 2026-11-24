# 用 389ds 作为 LDAPS 后端(rhds)

pre-requisite
- 所有命令都在 `bob/onprem/` 目录下执行,且 `oc` 已登录集群。

## 389ds放在集群内

reason: LDAPS 要求 `connectionUrl` 里的主机名出现在服务器证书的 SAN 中,并且 Keycloak pod 能解析、能连通它。部署在集群内,地址固定为:

```
ldaps://ds389.ibm-bob.svc.cluster.local:636
```

这个名字由 Service 提供,不依赖宿主机 IP、WiFi 或防火墙。


## 脚本分工

| 脚本 | 作用 |
| ---- | ---- |
| [`389ds.sh`](./389ds.sh) | 部署和维护 389ds:证书、工作负载、目录、Secret、用户、写入 `config-idp.yaml` |
| [`admin.sh`](./admin.sh) | 应用 IDP 配置和排查 |

## 调用顺序

```mermaid
flowchart TD
    A[1. 389ds.sh deploy] --> B[2. 检查 config-idp.yaml]
    B --> C["3 (optional). 389ds.sh addUser"]
    C --> D[4. admin.sh configureIdp]
    D --> E["5 (optional 检查结果). admin.sh idpStatus 和389ds.sh listUsers"]
    E --> F[6. 登录验证 ./admin.sh open]
    F -->G["7 (optional, 登录失败时). admin.sh loginTrace"]
```

### 1. 部署 389ds

```bash
./389ds.sh deploy
```

`deploy` 依次执行下面这些步骤,它们也可以单独运行:

| 步骤 | 函数 | 结果 |
| ---- | ---- | ---- |
| 1 | `certs` | 用 cert-manager 签发自签 CA `ds389-ca` 和服务器证书 `ds389-tls`,SAN 为 `ds389.ibm-bob.svc.cluster.local`、`ds389.ibm-bob.svc`、`ds389` |
| 2 | `adminSecret` | 随机生成 Directory Manager 密码,存入 Secret `ds389-admin` |
| 3 | `workload` | 创建 PVC、Deployment、Service;证书 Secret 按 `/data/tls/` 布局挂载,镜像启动时自动导入 |
| 4 | `initDirectory` | 创建后缀 `dc=example,dc=com`、`ou=People`、`ou=Groups`、`ou=ServiceAccounts`,以及绑定账号 `bob-svc`(随机密码存入 Secret `corp-ldap-bind`) |
| 5 | `caSecret` | 把 CA 证书存入 Secret `corp-ldap-ca`(key 为 `ca.crt`) |
| 6 | `idpInject` | 向 `config/config-idp.yaml` 的 `ldaps` 追加一项,并打印 diff |

所有步骤都可重复执行,已存在的资源会跳过。

验证:

```bash
./389ds.sh status
./389ds.sh testFromKeycloak   # Keycloak pod 到 389ds:636 的 TCP 连通
```

### 2. 检查 `config-idp.yaml`

确认三点:


- **`uuidLDAPAttribute: nsUniqueId`**。这个属性告诉 Keycloak 用 LDAP 条目的哪个属性作为用户的唯一、不变的 ID。这里选 `nsUniqueId` 是因为它是 389ds 自有属性,每个条目都保证存在,不依赖 `entryuuid` 插件(例如从旧版本迁移来的条目可能没有 `entryUUID`)。首次配置后不要再改,否则 Keycloak 会把已有用户当成新用户。



### 3. 添加用户

```bash
./389ds.sh addUser alice alice@example.com
```

密码在提示符处交互输入(不回显,只输入一次)

### 4. 应用 IDP 配置

```bash
./admin.sh configureIdp
```
默认等待 600 秒,可用 `BOB_IDP_WAIT_TIMEOUT=900` 调整。

### 5. 检查结果

```bash
./admin.sh idpStatus
```

期望看到:

```
NAME      READY   MESSAGE                         AGE
bob-idp   True    Last reconciliation succeeded   11h
389-ds  LDAPRegistered  True    LDAP provider registered in Keycloak
389-ds  LDAPReachable   True    LDAP server is reachable
389-ds  LDAPAuthenticated       True    LDAP bind credentials are valid
389-ds  LDAPUserSyncSucceeded   True    Initial LDAP user sync completed successfully

```

也可以单独验证 LDAPS 校验和 `bob-svc` 绑定:

```bash
./389ds.sh listUsers
```

### 6. 登录验证

```bash
./admin.sh open
```

打开输出里的登录页(本机 CRC 为 `https://bob.ibm-bob.apps-crc.testing`),用 LDAP 用户的邮箱和密码登录。证书是自签的,先用 `./bobctl get-ca-cert --output bob-ca.crt` 取 CA 并导入浏览器,或临时选择继续访问。

### 7. 登录失败时

```bash
./admin.sh loginTrace alice@example.com        # 默认看最近 15 分钟
SINCE=1h ./admin.sh loginTrace alice@example.com
```

它依次查 Keycloak 认证、`bob-authn` 权限查询、`bob-admin` 的 SCIM 开通。

## 常见现象

| 现象 | 原因与处理 |
| ---- | ---------- |
| 新用户首次登录出现 `account_not_provisioned`("Account Not Ready Yet") | 用户在 LDAP 认证通过的当下,Bob 里还没有这个账号;Keycloak 再通过 SCIM 同步过去,有 1 到 2 分钟的间隔。`loginTrace` 里看到 `SCIM Create: user provisioned` 后重新登录即可 |

## 可变参数

`389ds.sh` 顶部可通过环境变量覆盖:

| 变量 | 默认值 | 说明 |
| ---- | ------ | ---- |
| `BASE_DN` | `dc=example,dc=com` | 目录后缀 |
| `STORAGE` | `2Gi` | PVC 大小 |
| `BIND_SECRET` | `corp-ldap-bind` | 绑定密码 Secret,需与 `config-idp.yaml` 一致 |
| `CA_SECRET` | `corp-ldap-ca` | CA 证书 Secret,需与 `config-idp.yaml` 一致 |


## 清理

```bash
./389ds.sh uninstall # 会删除 Deployment、Service、证书、Issuer 和 Secret,但保留 PVC。
oc delete pvc ds389-data -n ibm-bob   # 彻底清除目录数据
```

它不会修改 `config-idp.yaml`,也不会删除 `BobIdp` 里已经配置的 provider;要移除 provider,需要先编辑 `config-idp.yaml` 再重新应用。

## 注意

- `ds389` 的 Directory Manager 密码取自 Secret:`oc get secret ds389-admin -n ibm-bob -o jsonpath='{.data.password}' | base64 -d`。
- 这是测试环境的部署:单副本、不做备份、CA 自签。生产环境请使用企业 LDAP 和企业 CA。
