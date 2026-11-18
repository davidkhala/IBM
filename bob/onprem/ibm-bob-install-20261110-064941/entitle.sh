set -e

# $IBM_ENTITLEMENT_KEY is required

if [ -z "${IBM_ENTITLEMENT_KEY}" ]; then
	set +o history
	read -s -p "Enter IBM Entitlement Key: " IBM_ENTITLEMENT_KEY && export IBM_ENTITLEMENT_KEY
	set -o history
	echo # linebreak
fi

podman() {
	echo $IBM_ENTITLEMENT_KEY | podman login -u cp --password-stdin cp.icr.io
	podman login --get-login cp.icr.io # expected output: cp
	podman login -u iamapikey icr.io   # interactive password input, using IBM Cloud API key
	podman login --get-login icr.io    # expected output: iamapikey

}

plan() {
	./bobctl generate-cluster-resources
	oc apply -f work/cluster-resources.yaml --force-conflicts --server-side
	./bobctl install --registry-creds "cp:${IBM_ENTITLEMENT_KEY}" --accept-license --model-config ../config/config-model-gateway.yaml --dry-run
}
install() {
	./bobctl install --registry-creds "cp:${IBM_ENTITLEMENT_KEY}" --accept-license
	oc logs -n ibm-bob-operators deployment/ibm-bob-operator -f
}

$@