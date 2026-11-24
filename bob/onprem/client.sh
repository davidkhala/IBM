set -e

# 用法: ./client.sh <function> [args]
#   getSelfSignedRootCA   从集群导出默认自签 root CA 到 config/bob-ca.crt
#   endpoints             列出 gateway 的 route host (api.bob.* 为 API 入口, bob.* 为 Web 登录入口)
#   shell [bob args...]   启动 bob shell
#							默认走 SSO 浏览器登录。
#							API key 登陆方式:
#							- export BOB_API_KEY=<inference-key>; ./client.sh shell
#							- export BOB_API_KEY=<general-key>; ./client.sh shell --team-id <team-id>
#   debian-trust-ca       把 root CA 导入 Debian/Ubuntu 系统信任库 (需 sudo), 供 bob-ide 校验 gateway 证书
#   ide [--system-certs]  启动 bob ide。
#							接入流程: ./client.sh getSelfSignedRootCA && ./client.sh debian-trust-ca && ./client.sh ide, 然后重启 bob-ide




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

# 查询路由并设置 GATEWAY_URL (API 入口) / LOGIN_URL (Web 登录入口)
envs() {
	local hosts=$(endpoints)
	GATEWAY_URL="https://$(echo "$hosts" | grep '^api\.')"
	LOGIN_URL="https://$(echo "$hosts" | grep -v '^api\.')"
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
		# 导入 CA 并重启后,IDE 仍报 UNABLE_TO_VERIFY_LEAF_SIGNATURE 时,才需要开启它
		filter="$filter | .\"http.experimental.systemCertificatesV2\" = true"
	fi
	updated=$(jq --arg url "$GATEWAY_URL" "$filter" "$settings")
	printf '%s\n' "$updated" >"$settings"
	echo "Please restart Bob IDE"
}

shell() {
	envs
	export NODE_EXTRA_CA_CERTS="$CA_FILE" BOB_GATEWAY_URL="$GATEWAY_URL" BOB_WEB_LOGIN_URL="$LOGIN_URL"
	case "$1" in
	chat | run | mcp | extension | acp) ;;
	*) set -- chat "$@" ;;
	esac
	exec bob --accept-license "$@"
}

"$@"
