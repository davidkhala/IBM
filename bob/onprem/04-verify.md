# 04 — 验证安装

```bash
export OPERATOR_NS=ibm-bob-operators
export INSTANCE_NS=ibm-bob
```

## 4.1 检查项

```bash
# Operator Pod 全部 Running
oc get pods -n $OPERATOR_NS

# Bob CR 状态为 Ready
oc get bob -n $INSTANCE_NS

# Operator 日志无阻塞 reconcile 的错误
oc logs -n $OPERATOR_NS deployment/ibm-bob-operator --tail=200
```

等待 Ready(可选):

```bash
oc wait bob/bob-cr -n $INSTANCE_NS --for=condition=Ready --timeout=30m
```

成功标准:

- [ ] Operator 命名空间内所有 Pod 为 `Running`
- [ ] `Bob` 自定义资源显示 `Ready`
- [ ] Operator 日志没有阻塞 reconcile / 部署进度的错误

## 4.2 补充检查

```bash
oc get pods -n $INSTANCE_NS
oc get pvc -n $INSTANCE_NS                 # 全部 Bound
oc get route -n $INSTANCE_NS
oc get certificate -n $INSTANCE_NS         # cert-manager 签发状态
oc get secret ibm-entitlement-key -n $INSTANCE_NS
oc get configmap bob-inference-model-config -n $INSTANCE_NS
oc get secret bob-inference-model-secrets -n $INSTANCE_NS
```

## 4.3 常见故障

| 现象 | 排查 |
| ---- | ---- |
| `bobctl install` 立即退出,提示缺 cert-manager CRD | 回到 [01-prerequisites.md](./01-prerequisites.md) 1.6 安装 cert-manager |
| Pod `ImagePullBackOff` / `ErrImagePull` | `oc describe pod <pod> -n $INSTANCE_NS` 查看事件;确认 `ibm-entitlement-key` 存在,key 有效(`podman login cp.icr.io`);air-gapped 核对 `imagePullPrefix` 并重跑 `bobctl verify-images` |
| PVC 一直 `Pending` | `oc get storageclass`;核对 `config.yaml` 的 `fileStorageClass`(RWX)与 `blockStorageClass`(RWO);`oc describe pvc` |
| Pod `Pending`,事件显示资源不足 | `oc describe node`;对照 1.5 的容量需求,必要时扩容 worker |
| Bob CR 长时间非 Ready | 看 Operator 日志;`oc get bob bob-cr -n $INSTANCE_NS -o yaml` 查看 `status.conditions` |
| 聊天无响应/模型报错 | 检查 `bob-inference` Pod 日志;确认已提供 `--model-config` 与密钥;从集群内验证到模型端点的网络与 TLS 信任 |
| 客户端 TLS 错误 | 多为客户端不信任 CA,见 [05-post-install.md](./05-post-install.md) |

查看推理服务日志:

```bash
oc logs -n $INSTANCE_NS deployment/bob-inference --tail=200
```

其他排查参考官方 [troubleshooting](https://bob.ibm.com/docs/ide/troubleshooting)。
