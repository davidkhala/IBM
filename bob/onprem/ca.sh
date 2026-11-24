set -e

# 列出所有 ingress 主机名 (全部必须写入证书 SAN)
getIngressHosts() {
	oc get ingress -n ibm-bob -o jsonpath='{range .items[*]}{range .spec.rules[*]}{.host}{"\n"}{end}{end}'
}

$@