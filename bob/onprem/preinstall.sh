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
	oc version --client # a match with the server version is not enforced

}
ocCheck() {
	oc whoami # kubeadmin
	oc whoami --show-server # https://api.crc.testing:6443

	local oc_min="4.20.0" # VERSION must be >= 4.20
	local oc_ver
	# history is in reverse chronological order; take the latest version with state=Completed (Partial entries from an in-progress upgrade are ignored)
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
	local base_url=$1 # https://httpbin-388394439802.asia-east2.run.app
	oc run net-test --rm -it --restart=Never --image=registry.access.redhat.com/ubi9/ubi-minimal -- curl -sS -o /dev/null -w '%{http_code}\n' --max-time 10 $base_url
}

$@
