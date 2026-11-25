set -e

if [ -z "${IBM_ENTITLEMENT_KEY}" ]; then
	set +o history
	read -s -p "Enter IBM Entitlement Key: " IBM_ENTITLEMENT_KEY && export IBM_ENTITLEMENT_KEY
	set -o history
	echo # linebreak
fi

plan() {
	cd ibm-bob-install-*
	./bobctl generate-cluster-resources
	oc apply -f work/cluster-resources.yaml --force-conflicts --server-side
	./bobctl install --registry-creds "cp:${IBM_ENTITLEMENT_KEY}" --accept-license --model-config ../config/config-model-gateway.yaml --dry-run
	cd -
}
install() {
	cd ibm-bob-install-*
	./bobctl install --registry-creds "cp:${IBM_ENTITLEMENT_KEY}" --accept-license
	cd -
	oc logs -n ibm-bob-operators deployment/ibm-bob-operator -f
}

$@