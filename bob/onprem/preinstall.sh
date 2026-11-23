set -e

binCheck() {

	helm version

	local helm_min="3.14.0"
	local helm_ver
	helm_ver=$(helm version --template '{{.Version}}' | sed 's/^v//; s/[-+].*//')
	if [ "$(printf '%s\n%s\n' "$helm_min" "$helm_ver" | sort -V | head -n1)" != "$helm_min" ]; then
		echo "ERROR: helm version $helm_ver is lower than required $helm_min" >&2
		return 1
	fi
	bash --version
	openssl version
	oc version --client # 不强制匹配server版本

}
ocCheck() {
	oc get clusterversion

	local oc_min="4.20.0" # VERSION 须为 >= 4.20
	local oc_ver
	# history 按时间倒序,取最近一个 state=Completed 的版本(升级中的 Partial 条目会被忽略)
	oc_ver=$(oc get clusterversion version -o jsonpath='{.status.history[?(@.state=="Completed")].version}' | awk '{print $1}' | sed 's/[-+].*//')
	if [ -z "$oc_ver" ]; then
		echo "ERROR: unable to determine completed OpenShift server version" >&2
		return 1
	fi
	if [ "$(printf '%s\n%s\n' "$oc_min" "$oc_ver" | sort -V | head -n1)" != "$oc_min" ]; then
		echo "ERROR: OpenShift version $oc_ver is lower than required $oc_min" >&2
		return 1
	fi
	echo "OpenShift version $oc_ver OK (>= $oc_min)"
}

netCheck() {
	local base_url=$1
	oc run net-test --rm -it --restart=Never --image=registry.access.redhat.com/ubi9/ubi-minimal -- curl -sS -o /dev/null -w '%{http_code}\n' --max-time 10 $base_url
}

$@
