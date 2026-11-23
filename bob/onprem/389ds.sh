set -e

# 在 OpenShift(CRC) 内部署 389ds,作为 BobIdp 的 rhds LDAPS 后端。
# 用法: ./389ds.sh <函数> [参数]
#   ./389ds.sh deploy                         # 证书 + 部署 + 初始化目录 + 创建 bobctl 需要的 Secret
#   ./389ds.sh addUser <uid> <mail> <password>
#   ./389ds.sh status | testLdaps | idpInject [配置文件] | uninstall
#
# 命名空间固定为 ibm-bob,Service 固定为 ds389,镜像固定为 quay.io/389ds/dirsrv:latest,均直接写在用到的地方。
# LDAPS 地址: ldaps://ds389.ibm-bob.svc.cluster.local:636  (证书 SAN 与之一致;
# 改 Service 名或命名空间时,要同时改 certs 的 dnsNames、workload 的 Service、testLdaps、_idpItem)

BASE_DN=${BASE_DN:-dc=example,dc=com}
STORAGE=${STORAGE:-2Gi}
# BobIdp 里这个 LDAP provider 的名字(Keycloak 组件显示名,首次配置后不要再改)
IDP_NAME=389-ds
IDP_CONFIG="$(cd "$(dirname "$0")" && pwd)/config/config-idp.yaml"
# bobctl configure-idp 引用的 Secret 名,需与 config-idp.yaml 一致
BIND_SECRET=${BIND_SECRET:-corp-ldap-bind}
CA_SECRET=${CA_SECRET:-corp-ldap-ca}
BIND_DN="cn=bob-svc,ou=ServiceAccounts,${BASE_DN}"


# 用 cert-manager 签发: 自签 CA -> CA Issuer -> 服务器证书(Secret ds389-tls: tls.crt/tls.key/ca.crt)
certs() {
	oc apply -n ibm-bob -f - <<EOF
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: ds389-selfsigned
spec:
  selfSigned: {}
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: ds389-ca
spec:
  isCA: true
  commonName: ds389-ca
  secretName: ds389-ca
  duration: 87600h
  privateKey:
    algorithm: RSA
    size: 2048
  issuerRef:
    name: ds389-selfsigned
    kind: Issuer
---
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: ds389-ca-issuer
spec:
  ca:
    secretName: ds389-ca
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: ds389-tls
spec:
  commonName: ds389.ibm-bob.svc.cluster.local
  dnsNames:
    - ds389.ibm-bob.svc.cluster.local
    - ds389.ibm-bob.svc
    - ds389
  secretName: ds389-tls
  duration: 8760h
  renewBefore: 720h
  privateKey:
    algorithm: RSA
    size: 2048
  usages:
    - digital signature
    - key encipherment
    - server auth
  issuerRef:
    name: ds389-ca-issuer
    kind: Issuer
EOF
	oc wait -n ibm-bob --for=condition=Ready certificate/ds389-ca certificate/ds389-tls --timeout=120s
}

# Directory Manager 密码,只在不存在时生成
adminSecret() {
	if oc get secret ds389-admin -n ibm-bob >/dev/null 2>&1; then
		echo "# secret ds389-admin exists, skip"
		return
	fi
	oc create secret generic ds389-admin -n ibm-bob --from-literal=password="$(openssl rand -hex 16)"
}

# dscontainer 启动时会读 /data/tls/{server.key,server.crt,ca/*.crt} 自动导入 NSS,
# 所以把 Secret 按这个布局投影到 /data/tls。
workload() {
	oc apply -n ibm-bob -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ds389-data
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: ${STORAGE}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ds389
  labels:
    app: ds389
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: ds389
  template:
    metadata:
      labels:
        app: ds389
    spec:
      containers:
        - name: ds389
          image: quay.io/389ds/dirsrv:latest
          env:
            - name: DS_DM_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: ds389-admin
                  key: password
          ports:
            - name: ldap
              containerPort: 3389
            - name: ldaps
              containerPort: 3636
          readinessProbe:
            exec:
              command: ["/usr/libexec/dirsrv/dscontainer", "-H"]
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 10
          livenessProbe:
            exec:
              command: ["/usr/libexec/dirsrv/dscontainer", "-H"]
            initialDelaySeconds: 60
            periodSeconds: 30
            timeoutSeconds: 10
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
          volumeMounts:
            - name: data
              mountPath: /data
            - name: tls
              mountPath: /data/tls
              readOnly: true
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: ds389-data
        - name: tls
          secret:
            secretName: ds389-tls
            items:
              - key: tls.key
                path: server.key
              - key: tls.crt
                path: server.crt
              - key: ca.crt
                path: ca/ca.crt
---
apiVersion: v1
kind: Service
metadata:
  name: ds389
spec:
  selector:
    app: ds389
  ports:
    - name: ldaps
      port: 636
      targetPort: ldaps
    - name: ldap
      port: 389
      targetPort: ldap
EOF
	oc rollout status deploy/ds389 -n ibm-bob --timeout=300s
}

# 在 ds389 pod 里以 Directory Manager 身份执行 ldap 命令,密码取自 pod 环境变量
# 用法: _ldap <命令及参数...>  (stdin 透传,用于 ldapadd 的 LDIF)
_ldap() {
	local cmd=$1
	shift
	oc exec -i -n ibm-bob deploy/ds389 -c ds389 -- \
		sh -c 'c=$1; shift; exec "$c" -x -H ldap://localhost:3389 -D "cn=Directory Manager" -w "$DS_DM_PASSWORD" "$@"' _ "$cmd" "$@"
}

_exists() {
	_ldap ldapsearch -LLL -s base -b "$1" dn >/dev/null 2>&1
}

# 创建 suffix + 基础 OU + bob-svc 绑定账号;可重复执行
initDirectory() {
	if oc exec -n ibm-bob deploy/ds389 -c ds389 -- sh -c \
		'dsconf -D "cn=Directory Manager" -w "$DS_DM_PASSWORD" ldap://localhost:3389 backend suffix list' |
		grep -qi "^${BASE_DN}"; then
		echo "# suffix ${BASE_DN} exists, skip"
	else
		oc exec -n ibm-bob deploy/ds389 -c ds389 -- sh -c \
			"dsconf -D 'cn=Directory Manager' -w \"\$DS_DM_PASSWORD\" ldap://localhost:3389 backend create --suffix '${BASE_DN}' --be-name userRoot --create-suffix"
	fi

	local ou
	for ou in People Groups ServiceAccounts; do
		if _exists "ou=${ou},${BASE_DN}"; then
			echo "# ou=${ou} exists, skip"
		else
			_ldap ldapadd <<EOF
dn: ou=${ou},${BASE_DN}
objectClass: top
objectClass: organizationalUnit
ou: ${ou}
EOF
		fi
	done

	bindAccount
}

# bob-svc: 随机密码,写入 Secret ${BIND_SECRET}(key=password)
bindAccount() {
	if oc get secret $BIND_SECRET -n ibm-bob >/dev/null 2>&1; then
		echo "# secret ${BIND_SECRET} exists, skip bind account"
		return
	fi
	local pw
	pw=$(openssl rand -hex 16)
	if _exists "$BIND_DN"; then
		_ldap ldappasswd -s "$pw" "$BIND_DN"
	else
		_ldap ldapadd <<EOF
dn: ${BIND_DN}
objectClass: top
objectClass: person
objectClass: organizationalPerson
objectClass: inetOrgPerson
cn: bob-svc
sn: bob-svc
uid: bob-svc
userPassword: ${pw}
EOF
	fi
	# 绑定账号需要能搜索 People/Groups
	_ldap ldapmodify <<EOF
dn: ${BASE_DN}
changetype: modify
add: aci
aci: (targetattr="*")(version 3.0; acl "bob-svc read"; allow (read,search,compare) userdn="ldap:///${BIND_DN}";)
EOF
	oc create secret generic $BIND_SECRET -n ibm-bob --from-literal=password="$pw"
}

# bobctl 的 ldapsCACertSecret(key=ca.crt)
caSecret() {
	if oc get secret $CA_SECRET -n ibm-bob >/dev/null 2>&1; then
		echo "# secret ${CA_SECRET} exists, skip"
		return
	fi
	oc get secret ds389-ca -n ibm-bob -o jsonpath='{.data.tls\.crt}' | base64 -d >/tmp/ds389-ca.crt
	oc create secret generic $CA_SECRET -n ibm-bob --from-file=ca.crt=/tmp/ds389-ca.crt
	rm -f /tmp/ds389-ca.crt
}

addUser() {
	local uid=$1 mail=$2 pw=$3
	if [ -z "$uid" ] || [ -z "$mail" ] || [ -z "$pw" ]; then
		echo "usage: $0 addUser <uid> <mail> <password>" >&2
		return 1
	fi
	if _exists "uid=${uid},ou=People,${BASE_DN}"; then
		echo "# user ${uid} exists, skip"
		return
	fi
	_ldap ldapadd <<EOF
dn: uid=${uid},ou=People,${BASE_DN}
objectClass: top
objectClass: person
objectClass: organizationalPerson
objectClass: inetOrgPerson
uid: ${uid}
cn: ${uid}
sn: ${uid}
givenName: ${uid}
mail: ${mail}
userPassword: ${pw}
EOF
}

deploy() {
	certs
	adminSecret
	workload
	initDirectory
	caSecret
	idpInject
}

# 从 pod 内走 Service 域名做 LDAPS 校验 + 用 bob-svc 绑定,等价于 Keycloak 的访问路径
testLdaps() {
	local pw
	pw=$(oc get secret $BIND_SECRET -n ibm-bob -o jsonpath='{.data.password}' | base64 -d)
	oc exec -n ibm-bob deploy/ds389 -c ds389 -- env LDAPTLS_CACERT=/data/tls/ca/ca.crt LDAPTLS_REQCERT=demand \
		ldapsearch -LLL -H "ldaps://ds389.ibm-bob.svc.cluster.local:636" -D "$BIND_DN" -w "$pw" -b "ou=People,${BASE_DN}" -s one uid mail
}

# 从 Keycloak pod 里测试到 389ds LDAPS 端口的 TCP 连通性(验证 Service 域名解析和网络策略)
testFromKeycloak() {
	oc exec -n ibm-bob bob-keycloak-0 -c keycloak -- bash -c \
		'timeout 5 bash -c "echo > /dev/tcp/ds389.ibm-bob.svc.cluster.local/636"' &&
		echo "# reachable from keycloak" || { echo "# unreachable from keycloak" >&2; return 1; }
}

# 要加入 ldaps 的列表项(2 空格缩进的 "- ",字段 4 空格,与 configure-idp.sh 的解析一致)
_idpItem() {
	cat <<EOF
  - name: ${IDP_NAME}
    vendor: rhds
    connectionUrl: ldaps://ds389.ibm-bob.svc.cluster.local:636
    usersDn: ou=People,${BASE_DN}
    usernameLDAPAttribute: uid
    rdnLDAPAttribute: uid
    uuidLDAPAttribute: nsUniqueId
    userObjectClasses: inetOrgPerson,organizationalPerson,person
    bindDn: ${BIND_DN}
    bindPasswordSecret:
      name: ${BIND_SECRET}
      key: password
    ldapsCACertSecret:
      name: ${CA_SECRET}
      key: ca.crt
    useTruststoreSpi: always
    userSync:
      enabled: true
EOF
}

# 只往 config-idp.yaml 的 ldaps 里追加一个列表项,不改动其余任何内容(模板、注释、其他项)。
#   - 已有名为 ${IDP_NAME} 的项:        跳过
#   - 没有顶层 ldaps: (仍是注释):       报错退出。取消注释是手工的事,脚本不做
#   - 顶层 ldaps: 下没有真实列表项:      新项紧贴在 ldaps: 之后,参考注释块顺延到新项后面
#   - 顶层 ldaps: 下已有真实列表项:      新项追加到最后一项之后
# 新项必须在参考注释块之前: configure-idp.sh 遇到第 0 列的非空行(含 # 注释)就认为 ldaps 块结束。
idpInject() {
	local file=${1:-$IDP_CONFIG} tmp
	if [ ! -f "$file" ]; then
		echo "# $file not found" >&2
		return 1
	fi
	if grep -qE "^  - name: ${IDP_NAME}[[:space:]]*$" "$file"; then
		echo "# ldaps item '${IDP_NAME}' exists in $file, skip"
		return
	fi
	if ! grep -qE '^ldaps:[[:space:]]*(#.*)?$' "$file"; then
		echo "# $file 里没有顶层 'ldaps:' (被注释了?),请先手工取消注释,再重新执行" >&2
		return 1
	fi
	tmp=$(mktemp)
	# 方案: 新项紧贴在 "ldaps:" 之后,其后的参考注释块原封不动。
	# 若 ldaps 下已有真实列表项 ("  - "),则插在最后一项的末尾,保持各项连续。
	ITEM="$(_idpItem)" awk '
		{ l[NR] = $0 }
		END {
			start = 0
			for (i = 1; i <= NR; i++) if (l[i] ~ /^ldaps:[ \t]*(#.*)?$/) { start = i; break }
			last = start
			for (i = start + 1; i <= NR; i++) {
				if (l[i] ~ /^[^ \t#]/) break
				if (l[i] ~ /^[ \t]/ && l[i] !~ /^[ \t]*(#.*)?$/) last = i
			}
			for (i = 1; i <= last; i++) print l[i]
			print ENVIRON["ITEM"]
			for (i = last + 1; i <= NR; i++) print l[i]
		}' "$file" >"$tmp"
	echo "# $file: 追加 ldaps 项 '${IDP_NAME}',变更如下:"
	diff -u "$file" "$tmp" || true
	cat "$tmp" >"$file"
	rm -f "$tmp"
}

status() {
	oc get pods,svc,pvc,certificate -n ibm-bob -l 'app=ds389' 2>&1
	oc get certificate,secret -n ibm-bob | grep -E "ds389|${BIND_SECRET}|${CA_SECRET}"
}

uninstall() {
	oc delete deploy/ds389 svc/ds389 -n ibm-bob --ignore-not-found
	oc delete certificate ds389-tls ds389-ca -n ibm-bob --ignore-not-found
	oc delete issuer ds389-ca-issuer ds389-selfsigned -n ibm-bob --ignore-not-found
	oc delete secret ds389-tls ds389-ca ds389-admin $BIND_SECRET $CA_SECRET -n ibm-bob --ignore-not-found
	echo "# PVC ds389-data 保留; 彻底清除: oc delete pvc ds389-data -n ibm-bob"
}

$@
