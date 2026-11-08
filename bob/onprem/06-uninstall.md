# 06 — 卸载

**破坏性操作**:会删除 Bob 及其数据。执行前确认目标集群,并按需先做备份。步骤有先后依赖,不可跳过。

```bash
export OPERATOR_NS=ibm-bob-operators
export INSTANCE_NS=ibm-bob
oc whoami --show-server
```

## 6.1 删除 Bob CR 与 IDP CR

```bash
oc delete -n $INSTANCE_NS bob/bob-cr bobidp/bob-idp --wait=false
```

## 6.2 移除 IDP finalizer

finalizer 可能阻塞删除:

```bash
oc patch bobidp/bob-idp -n $INSTANCE_NS --type=merge -p '{"metadata":{"finalizers":[]}}'
```

## 6.3 卸载 Helm release

```bash
helm uninstall ibm-bob
```

## 6.4 删除集群资源(二选一)

**保留集群级资源**(CRD、ClusterRole 等)——仅删除命名空间:

```bash
oc delete namespace $INSTANCE_NS
oc delete namespace $OPERATOR_NS
```

**彻底清理**(退役环境时使用):

```bash
oc delete -f work/cluster-resources.yaml --ignore-not-found
```

`work/cluster-resources.yaml` 不存在时先 `./bobctl generate-cluster-resources` 重新生成。彻底清理时同样需要删除上述两个命名空间。

## 6.5 本地清理(可选)

```powershell
podman logout cp.icr.io
Remove-Item Env:\IBM_ENTITLEMENT_KEY
```
