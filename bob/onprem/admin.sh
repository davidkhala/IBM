set -e

bobStatus() {
	oc get deployment -n ibm-bob-operators
	echo "# oc get bob -n ibm-bob"
	oc get bob -n ibm-bob
	oc get pods -n ibm-bob -l app=bob-inference
}
updateModel() {
	cd ibm-bob-install-*
	./bobctl update-model-config --model-config ../config/config-model-gateway.yaml --update-secrets --dry-run
	./bobctl update-model-config --model-config ../config/config-model-gateway.yaml --update-secrets
	cd -
	oc rollout restart deploy/bob-inference -n ibm-bob
}

# 用法: ./admin.sh configureIdp [--dry-run]
configureIdp() {
	cd ibm-bob-install-*
	./bobctl configure-idp --config ../config/config-idp.yaml --dry-run
	if [ "$1" != "--dry-run" ]; then
		./bobctl configure-idp --config ../config/config-idp.yaml
	fi
	cd -
}
idpStatus() {
	oc get bobidp -n ibm-bob
	oc get bobidp bob-idp -n ibm-bob -o go-template='{{range .status.ldaps}}{{$p := .name}}{{range .conditions}}{{$p}}{{"\t"}}{{.type}}{{"\t"}}{{.status}}{{"\t"}}{{.message}}{{"\n"}}{{end}}{{end}}'
}

open() {
	# open bob portal
	echo "https://$(oc get routes -n ibm-bob -o json | jq -r '.items[] | select(.spec.to.name=="bob-gateway") | .spec.host | select(startswith("bob."))' | head -1)"
	xdg-open "https://$(oc get routes -n ibm-bob -o json | jq -r '.items[] | select(.spec.to.name=="bob-gateway") | .spec.host | select(startswith("bob."))' | head -1)"
}
# 按邮箱追踪一次登录: Keycloak 认证 -> bob-authn 权限查询 -> bob-admin 的 SCIM 开通
# 用法: ./admin.sh loginTrace alice@example.com   (SINCE=30m 可调整时间范围,默认 15m)
# 常见现象: 新用户首次登录出现 account_not_provisioned,是因为 bob-authn 查权限(15:31)早于 SCIM 同步(间隔 1~2 分钟),
#           看到 "SCIM Create: user provisioned" 后重新登录即可。
loginTrace() {
	local email=${1:?usage: ./admin.sh loginTrace <email>} since=${SINCE:-15m}
	local user=${email%@*}
	echo "# keycloak (user=$user)"
	oc logs -n ibm-bob bob-keycloak-0 -c keycloak --since=$since 2>&1 | grep -E "user=$user|userName.*$user" | tail -8 || true
	echo "# bob-authn"
	oc logs -n ibm-bob deploy/bob-authn --since=$since 2>&1 | grep -F "$email" | cut -c1-300 | tail -8 || true
	echo "# bob-admin (SCIM)"
	oc logs -n ibm-bob deploy/bob-admin --since=$since 2>&1 | grep -F "$email" | grep -i scim | cut -c1-300 | tail -5 || true
}

# Usage: BOB_API_KEY=<Inference-scope API key> ./admin.sh modelStatus [slot]
# slot: one of the reserved model name slots of the model gateway.
#   premium-ide (default) - interactive chat
#   security              - guardrail / security checks
#   background            - background and autonomous agent tasks
modelStatus() {
	local slot=${1:-premium-ide}
	case "$slot" in
	premium-ide | security | background) ;;
	*)
		echo "# invalid slot '$slot', expected: premium-ide | security | background" >&2
		return 2
		;;
	esac
	oc logs -n ibm-bob deploy/bob-inference --since=5m
	oc exec -n ibm-bob deploy/bob-gateway -- curl -sk https://bob-inference.ibm-bob.svc.cluster.local:7330/v1/model/info | jq .

	# End-to-end test through the external gateway, so authn/authz, subscription and budget checks are all exercised.
	if [ -z "$BOB_API_KEY" ]; then
		echo "# BOB_API_KEY not set, skip end-to-end inference test"
		return
	fi
	local host resp finish
	host=$(oc get route -n ibm-bob -o json | jq -r '.items[].spec.host | select(startswith("api.bob."))' | head -1)
	# the API key goes through stdin (-H @-) to keep it out of the process list
	resp=$(printf 'X-API-Key: %s\n' "$BOB_API_KEY" | curl -sk -m 120 -H @- -H 'Content-Type: application/json' \
		"https://$host/inference/v1/chat/completions" \
		-d "$(jq -nc --arg m "$slot" '{model:$m,messages:[{role:"user",content:"Reply with exactly one word: pong"}]}')")
	echo "$resp" | jq '{model, content: .choices[0].message.content, finish_reason: .choices[0].finish_reason, usage}'
	finish=$(echo "$resp" | jq -r '.choices[0].finish_reason // empty')
	if [ "$finish" != "stop" ]; then
		echo "# FAILED: expected finish_reason=stop, got '${finish:-none}'" >&2
		return 1
	fi
	echo "# OK: slot '$slot' answered via https://$host"
}

installCertman() {
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
certmanStatus() {
	# Verify installation
	oc get csv -n cert-manager-operator
	oc get pods -n cert-manager
	oc get crd certificates.cert-manager.io issuers.cert-manager.io clusterissuers.cert-manager.io certificaterequests.cert-manager.io # 核心 CRD 存在检查
}
gcp() {
	local path_to_json=$1
	base64 -i $path_to_json | tr -d '\n'
}

$@
