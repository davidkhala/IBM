# 05 — 安装后任务


## 5.1 TLS 证书

`bob-ide` / `bob-shell` 在证书被客户端信任前无法连接。三选一:

### A. 企业/公共证书(推荐)

0. 证书要求
  - 私钥未加密
  - 含完整证书链、
  - PEM 格式
  - SAN 覆盖所有hostname，hostname可以通过`./ca.sh getIngressHosts`获取
1. 创建 Secret 并应用:

   ```bash
   oc create secret generic my-tls-secret \
     --from-file=tls.crt=tls.crt \
     --from-file=tls.key=tls.key \
     --from-file=ca.crt=ca.crt \
     -n ibm-bob

   ./bobctl setup-route --tls-secret my-tls-secret
   ```

   公共可信证书可用 `oc create secret tls my-tls-secret --cert=... --key=... -n ibm-bob`。更新已存在的 Secret 时在 `oc create ... --dry-run=client -o yaml` 后接 `| oc apply -f -`。



如果需要撤销自定义 TLS 证书,回到 IBM Bob 的默认证书
```
./bobctl reset-route
```

### C. 默认自签证书

未配置外部证书时使用 cert-manager 签发的自签证书。判断当前状态:


```bash
oc get secret bob-external-tls -n ibm-bob -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -issuer
```

issuer 为 `CN=Bob Internal CA` 即默认自签。导出并分发 CA:

```bash
./bobctl get-ca-cert --output bob-ca.crt
```

用户把 `bob-ca.crt` 导入操作系统信任库。





## 5.2 获取并分发 endpoint

```bash
oc get route -n ibm-bob -l app.kubernetes.io/component=bob-gateway 
  -o custom-columns=NAME:.metadata.name,HOST:.spec.host
```

gateway 有两个 route:

- `bob.<域名>`:Web 登录入口(`./admin.sh open` 打开的就是它)
- `api.bob.<域名>`:API 入口(`/inference/v1/...`)


客户端接入方式见官方 [Accessing Bob self-hosted](https://bob.ibm.com/docs/ide/enterprise/on-premises/accessing)。
