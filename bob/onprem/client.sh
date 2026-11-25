set -e

# Usage: ./client.sh <function> [args]
#   getSelfSignedRootCA   Export the default self-signed root CA from the cluster to config/bob-ca.crt
#   endpoints             List the gateway route hosts (api.bob.* is the API entry point, bob.* is the web login entry point)
#   shell [bob args...]   Start bob shell
#							Uses browser SSO login by default.
#							To log in with an API key:
#							- export BOB_API_KEY=<inference-key>; ./client.sh shell
#							- export BOB_API_KEY=<general-key>; ./client.sh shell --team-id <team-id>
#   debian-trust-ca       Import the root CA into the Debian/Ubuntu system trust store (requires sudo) so bob-ide can verify the gateway certificate
#   ide [--system-certs]  Start bob ide.

cd "$(dirname "$(readlink -f "$0")")"

CA_FILE="$PWD/config/bob-ca.crt"

getSelfSignedRootCA() {
	cd ibm-bob-install-*
	./bobctl get-ca-cert --output $CA_FILE
	cd -
}

endpoints() {
	oc get route -n ibm-bob -l app.kubernetes.io/component=bob-gateway -o jsonpath='{range .items[*]}{.spec.host}{"\n"}{end}'
}

# Query the routes and export BOB_GATEWAY_URL (API entry point) / BOB_WEB_LOGIN_URL (web login entry point)
envs() {
	local hosts=$(endpoints)
	export BOB_GATEWAY_URL="https://$(echo "$hosts" | grep '^api\.')"
	export BOB_WEB_LOGIN_URL="https://$(echo "$hosts" | grep -v '^api\.')"
}

debian-trust-ca() {
	[ -f "$CA_FILE" ] || getSelfSignedRootCA
	sudo cp "$CA_FILE" /usr/local/share/ca-certificates/bob-ca.crt
	sudo update-ca-certificates
}

ide() {
	local settings="$HOME/.bob/settings/settings.json" filter updated
	envs
	filter='.gatewayUrl = $url'
	if [ "$1" = "--system-certs" ]; then
		# Only enable this if the IDE still reports UNABLE_TO_VERIFY_LEAF_SIGNATURE after importing the CA and restarting
		filter="$filter | .\"http.experimental.systemCertificatesV2\" = true"
	fi
	updated=$(jq --arg url "$BOB_GATEWAY_URL" "$filter" "$settings")
	printf '%s\n' "$updated" >"$settings"
	echo "Please restart Bob IDE"
}

shell() {
	envs
	export NODE_EXTRA_CA_CERTS="$CA_FILE"
	case "$1" in
	chat | run | mcp | extension | acp) ;;
	*) set -- chat "$@" ;;
	esac
	exec bob --accept-license "$@"
}

"$@"
