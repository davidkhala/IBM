# 05 — 安装后任务

```bash
export INSTANCE_NS=ibm-bob
```

## 5.1 TLS 证书

`bob-ide` / `bob-shell` 在证书被客户端信任前无法连接。三选一:

### A. 企业/公共证书(推荐)

1. 列出所有 ingress 主机名,全部必须写入证书 SAN:

   ```bash
   oc get ingress -n $INSTANCE_NS \
     -o jsonpath='{range .items[*]}{range .spec.rules[*]}{.host}{"\n"}{end}{end}'
   ```

2. 证书要求:私钥未加密、含完整证书链、PEM 格式、SAN 覆盖所有主机名。
3. 创建 Secret 并应用:

   ```bash
   oc create secret generic my-tls-secret \
     --from-file=tls.crt=tls.crt \
     --from-file=tls.key=tls.key \
     --from-file=ca.crt=ca.crt \
     -n $INSTANCE_NS

   ./bobctl setup-route --tls-secret my-tls-secret
   ```

   公共可信证书可用 `oc create secret tls my-tls-secret --cert=... --key=... -n $INSTANCE_NS`。更新已存在的 Secret 时在 `oc create ... --dry-run=client -o yaml` 后接 `| oc apply -f -`。

### B. 用 OpenSSL 签发私有 CA 证书

```bash
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 365 -out ca.crt -subj "/CN=<BOB_HOSTNAME> CA"

openssl genrsa -out tls.key 4096
```

`san.cnf`(按实际主机名增减 `DNS.n`):

```ini
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = <BOB_HOSTNAME_1>

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = <BOB_HOSTNAME_1>
DNS.2 = <BOB_HOSTNAME_2>
```

```bash
openssl req -new -key tls.key -out tls.csr -config san.cnf
openssl x509 -req -in tls.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out tls.crt -days 365 -extensions v3_req -extfile san.cnf

oc create secret generic my-tls-secret \
  --from-file=tls.crt=tls.crt --from-file=tls.key=tls.key --from-file=ca.crt=ca.crt \
  -n $INSTANCE_NS
./bobctl setup-route --tls-secret my-tls-secret
```

`setup-route` 参数:`--tls-secret`、`--no-wait`、`--dry-run`。CA 为客户端未信任的私有 CA 时,需要把 `ca.crt` 分发给用户。

### C. 默认自签证书

未配置外部证书时使用 cert-manager 签发的自签证书。判断当前状态:

```bash
oc get secret bob-external-tls -n $INSTANCE_NS \
  -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -issuer
```

issuer 为 `CN=Bob Internal CA` 即默认自签。导出并分发 CA:

```bash
./bobctl get-ca-cert --output bob-ca.crt
```

用户把 `bob-ca.crt` 导入操作系统信任库。

### 验证与回退

```bash
echo | openssl s_client -connect <hostname>:443 -servername <hostname> 2>/dev/null \
  | openssl x509 -noout -issuer -subject -dates
```

检查 issuer、SAN、有效期。回退到默认自签:`./bobctl reset-route`。

## 5.2 IDP / LDAP(可选)

准备:LDAP URL、用户与组搜索基、绑定账号、LDAPS 私有 CA 证书。

```bash
./bobctl configure-idp --config my-idp.yaml --dry-run
./bobctl configure-idp --config my-idp.yaml
# 默认等待 600 秒,可调整:
BOB_IDP_WAIT_TIMEOUT=900 ./bobctl configure-idp --config my-idp.yaml
```

验证:

```bash
oc get bobidp -n $INSTANCE_NS
oc get bobidp bob-idp -n $INSTANCE_NS -o yaml
```

期望的 conditions:`Ready`、`LDAPRegistered`、`LDAPReachable`、`LDAPAuthenticated`,以及启用 `userSync.enabled: true` 时的 `LDAPUserSyncSucceeded`。一个文件内可在 `ldaps` 列表配置多个 LDAP provider。

## 5.3 用户访问

Bob 自带 Keycloak。二选一:

- **LDAP/AD 联邦**:5.2 完成后用企业账号登录。
- **Keycloak 直接用户**:在 Keycloak 中创建用户,适合评估环境。

## 5.4 获取并分发 endpoint

```bash
oc get route -n $INSTANCE_NS -l app.kubernetes.io/component=gateway \
  -o jsonpath='{.items[0].spec.host}'
```

endpoint URL 为 `https://<上述 host>`。无 route 时先确认 `oc get bob -n $INSTANCE_NS` 为 `Ready`。

提供给用户:

| 项 | 是否必需 |
| -- | -------- |
| Bob endpoint URL | 是 |
| CA 证书 `bob-ca.crt` | 仅自签/私有 CA 时 |
| 认证信息 | 是 |

客户端接入方式见官方 [Accessing Bob self-hosted](https://bob.ibm.com/docs/ide/enterprise/on-premises/accessing)。

## 检查清单

- [ ] 外部 endpoint 证书可被客户端信任(或已分发 CA)
- [ ] IDP/Keycloak 用户可登录(如适用)
- [ ] endpoint URL 与认证方式已告知用户
- [ ] 已按组织要求在 OpenShift 层配置安全日志、审计与监控(Bob 自身不提供)
