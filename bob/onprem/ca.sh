set -e

# List all ingress hostnames (all of them must be included in the certificate SAN)
getIngressHosts() {
	oc get ingress -n ibm-bob -o jsonpath='{range .items[*]}{range .spec.rules[*]}{.host}{"\n"}{end}{end}'
}

$@