set -e

bob-status() {
	oc get deployment -n ibm-bob-operators
	echo "# oc get bob -n ibm-bob"
	oc get bob -n ibm-bob
}
update-model() {
	./bobctl update-model-config --model-config ../config/config-model-gateway.yaml --update-secrets --dry-run
	./bobctl update-model-config --model-config ../config/config-model-gateway.yaml --update-secrets
}

install-certman() {
	# Create the operator namespace
	if oc get project cert-manager-operator >/dev/null 2>&1; then
		echo "# project cert-manager-operator exists, skip"
	else
		oc new-project cert-manager-operator
	fi

	# Create the OperatorGroup (AllNamespaces mode, no targetNamespaces)
	# A namespace allows only one OperatorGroup, so skip if any exists (the name may be auto-generated)
	if [ -n "$(oc get operatorgroup -n cert-manager-operator -o name 2>/dev/null)" ]; then
		echo "# operatorgroup in cert-manager-operator exists, skip"
	else
		oc apply -f - <<EOF
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: cert-manager-operator
  namespace: cert-manager-operator
spec:
  upgradeStrategy: Default
EOF
	fi

	# Create the Subscription
	if oc get subscription.operators.coreos.com openshift-cert-manager-operator -n cert-manager-operator >/dev/null 2>&1; then
		echo "# subscription openshift-cert-manager-operator exists, skip"
	else
		oc apply -f - <<EOF
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: openshift-cert-manager-operator
  namespace: cert-manager-operator
spec:
  channel: stable-v1
  name: openshift-cert-manager-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
  installPlanApproval: Automatic
EOF
	fi

}
certman-status() {
	# Verify installation
	oc get csv -n cert-manager-operator
	oc get pods -n cert-manager

}
$@
