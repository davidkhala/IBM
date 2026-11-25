set -e

# Deploy 389ds inside OpenShift (CRC) as the rhds LDAPS backend for BobIdp.
# Usage: ./ldap.sh <function> [args]
#   ./ldap.sh deploy                         # certificates + deployment + directory init + create the Secrets bobctl needs
#   ./ldap.sh addUser <uid> <mail>           # password is entered interactively at the prompt
#   ./ldap.sh status | listUsers | idpInject [config file] | uninstall
#
# LDAPS address: ldaps://ds389.ibm-bob.svc.cluster.local:636  (matches the certificate SAN;
# if you change the Service name or namespace, also change the dnsNames in certs, the Service in workload, listUsers, and _idpItem)

BASE_DN=${BASE_DN:-dc=example,dc=com}
STORAGE=${STORAGE:-2Gi}
# Name of this LDAP provider in BobIdp (Keycloak component display name; do not change after the initial configuration)
IDP_NAME=389-ds
IDP_CONFIG="$(cd "$(dirname "$0")" && pwd)/../../config/config-idp.yaml"
# Secret names referenced by bobctl configure-idp; must match config-idp.yaml
BIND_SECRET=${BIND_SECRET:-corp-ldap-bind}
CA_SECRET=${CA_SECRET:-corp-ldap-ca}
BIND_DN="cn=bob-svc,ou=ServiceAccounts,${BASE_DN}"


# Issue with cert-manager: self-signed CA -> CA Issuer -> server certificate (Secret ds389-tls: tls.crt/tls.key/ca.crt)
certs() {
	oc apply -n ibm-bob -f - <<EOF
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: ds389-selfsigned
spec:
  selfSigned: {}
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: ds389-ca
spec:
  isCA: true
  commonName: ds389-ca
  secretName: ds389-ca
  duration: 87600h
  privateKey:
    algorithm: RSA
    size: 2048
  issuerRef:
    name: ds389-selfsigned
    kind: Issuer
---
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: ds389-ca-issuer
spec:
  ca:
    secretName: ds389-ca
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: ds389-tls
spec:
  commonName: ds389.ibm-bob.svc.cluster.local
  dnsNames:
    - ds389.ibm-bob.svc.cluster.local
    - ds389.ibm-bob.svc
    - ds389
  secretName: ds389-tls
  duration: 8760h
  renewBefore: 720h
  privateKey:
    algorithm: RSA
    size: 2048
  usages:
    - digital signature
    - key encipherment
    - server auth
  issuerRef:
    name: ds389-ca-issuer
    kind: Issuer
EOF
	oc wait -n ibm-bob --for=condition=Ready certificate/ds389-ca certificate/ds389-tls --timeout=120s
}

# Directory Manager password; generated only if it does not already exist
adminSecret() {
	if oc get secret ds389-admin -n ibm-bob >/dev/null 2>&1; then
		echo "# secret ds389-admin exists, skip"
		return
	fi
	oc create secret generic ds389-admin -n ibm-bob --from-literal=password="$(openssl rand -hex 16)"
}

# On startup, dscontainer reads /data/tls/{server.key,server.crt,ca/*.crt} and imports them into NSS automatically,
# so the Secret is projected into /data/tls using this layout.
workload() {
	oc apply -n ibm-bob -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ds389-data
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: ${STORAGE}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ds389
  labels:
    app: ds389
spec:
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app: ds389
  template:
    metadata:
      labels:
        app: ds389
    spec:
      containers:
        - name: ds389
          image: quay.io/389ds/dirsrv:latest
          env:
            - name: DS_DM_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: ds389-admin
                  key: password
          ports:
            - name: ldap
              containerPort: 3389
            - name: ldaps
              containerPort: 3636
          readinessProbe:
            exec:
              command: ["/usr/libexec/dirsrv/dscontainer", "-H"]
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 10
          livenessProbe:
            exec:
              command: ["/usr/libexec/dirsrv/dscontainer", "-H"]
            initialDelaySeconds: 60
            periodSeconds: 30
            timeoutSeconds: 10
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
          volumeMounts:
            - name: data
              mountPath: /data
            - name: tls
              mountPath: /data/tls
              readOnly: true
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: ds389-data
        - name: tls
          secret:
            secretName: ds389-tls
            items:
              - key: tls.key
                path: server.key
              - key: tls.crt
                path: server.crt
              - key: ca.crt
                path: ca/ca.crt
---
apiVersion: v1
kind: Service
metadata:
  name: ds389
spec:
  selector:
    app: ds389
  ports:
    - name: ldaps
      port: 636
      targetPort: ldaps
    - name: ldap
      port: 389
      targetPort: ldap
EOF
	oc rollout status deploy/ds389 -n ibm-bob --timeout=300s
	waitDmPassword
}

# The readinessProbe only checks the LDAPI auto-bind, while dscontainer initializes with a temporary password and only later sets DS_DM_PASSWORD,
# so the password may not be in effect yet when the Pod is Ready (a bind then fails with 49 Invalid credentials). Here we do a real bind with the password and continue only once it succeeds.
waitDmPassword() {
	local i
	for i in $(seq 1 30); do
		if oc exec -n ibm-bob deploy/ds389 -c ds389 -- sh -c \
			'ldapwhoami -x -H ldap://localhost:3389 -D "cn=Directory Manager" -w "$DS_DM_PASSWORD"' >/dev/null 2>&1; then
			return
		fi
		sleep 2
	done
	echo "# Directory Manager password did not take effect within 60 seconds; check: oc logs -n ibm-bob deploy/ds389" >&2
	return 1
}

# Run an ldap command inside the ds389 pod as Directory Manager; the password is taken from the pod environment variable
# Usage: _ldap <command and args...>  (stdin is passed through, used for the LDIF of ldapadd)
_ldap() {
	local cmd=$1
	shift
	oc exec -i -n ibm-bob deploy/ds389 -c ds389 -- \
		sh -c 'c=$1; shift; exec "$c" -x -H ldap://localhost:3389 -D "cn=Directory Manager" -w "$DS_DM_PASSWORD" "$@"' _ "$cmd" "$@"
}

_exists() {
	_ldap ldapsearch -LLL -s base -b "$1" dn >/dev/null 2>&1
}

# Create the suffix + base OUs + the bob-svc bind account; safe to run repeatedly
initDirectory() {
	if oc exec -n ibm-bob deploy/ds389 -c ds389 -- sh -c \
		'dsconf -D "cn=Directory Manager" -w "$DS_DM_PASSWORD" ldap://localhost:3389 backend suffix list' |
		grep -qi "^${BASE_DN}"; then
		echo "# suffix ${BASE_DN} exists, skip"
	else
		oc exec -n ibm-bob deploy/ds389 -c ds389 -- sh -c \
			"dsconf -D 'cn=Directory Manager' -w \"\$DS_DM_PASSWORD\" ldap://localhost:3389 backend create --suffix '${BASE_DN}' --be-name userRoot --create-suffix"
	fi

	local ou
	for ou in People Groups ServiceAccounts; do
		if _exists "ou=${ou},${BASE_DN}"; then
			echo "# ou=${ou} exists, skip"
		else
			_ldap ldapadd <<EOF
dn: ou=${ou},${BASE_DN}
objectClass: top
objectClass: organizationalUnit
ou: ${ou}
EOF
		fi
	done

	bindAccount
}

# bob-svc: random password, written to Secret ${BIND_SECRET} (key=password)
bindAccount() {
	if oc get secret $BIND_SECRET -n ibm-bob >/dev/null 2>&1; then
		echo "# secret ${BIND_SECRET} exists, skip bind account"
		return
	fi
	local pw
	pw=$(openssl rand -hex 16)
	if _exists "$BIND_DN"; then
		_ldap ldappasswd -s "$pw" "$BIND_DN"
	else
		_ldap ldapadd <<EOF
dn: ${BIND_DN}
objectClass: top
objectClass: person
objectClass: organizationalPerson
objectClass: inetOrgPerson
cn: bob-svc
sn: bob-svc
uid: bob-svc
userPassword: ${pw}
EOF
	fi
	# The bind account must be able to search People/Groups
	_ldap ldapmodify <<EOF
dn: ${BASE_DN}
changetype: modify
add: aci
aci: (targetattr="*")(version 3.0; acl "bob-svc read"; allow (read,search,compare) userdn="ldap:///${BIND_DN}";)
EOF
	oc create secret generic $BIND_SECRET -n ibm-bob --from-literal=password="$pw"
}

# bobctl's ldapsCACertSecret (key=ca.crt)
caSecret() {
	if oc get secret $CA_SECRET -n ibm-bob >/dev/null 2>&1; then
		echo "# secret ${CA_SECRET} exists, skip"
		return
	fi
	oc get secret ds389-ca -n ibm-bob -o jsonpath='{.data.tls\.crt}' | base64 -d >/tmp/ds389-ca.crt
	oc create secret generic $CA_SECRET -n ibm-bob --from-file=ca.crt=/tmp/ds389-ca.crt
	rm -f /tmp/ds389-ca.crt
}

addUser() {
	# Interactive password capture
	local uid=$1 mail=$2 pw
	if [ -z "$uid" ] || [ -z "$mail" ]; then
		echo "usage: $0 addUser <uid> <mail>" >&2
		return 1
	fi
	if _exists "uid=${uid},ou=People,${BASE_DN}"; then
		echo "# user ${uid} exists, skip"
		return
	fi
	if [ ! -t 0 ]; then
		echo "# addUser must be run in an interactive terminal so the password can be entered" >&2
		return 1
	fi
	read -rsp "Password for ${uid}: " pw
	echo
	if [ -z "$pw" ]; then
		echo "# password must not be empty" >&2
		return 1
	fi
	_ldap ldapadd <<EOF
dn: uid=${uid},ou=People,${BASE_DN}
objectClass: top
objectClass: person
objectClass: organizationalPerson
objectClass: inetOrgPerson
uid: ${uid}
cn: ${uid}
sn: ${uid}
givenName: ${uid}
mail: ${mail}
userPassword:: $(printf '%s' "$pw" | base64 -w0)
EOF
}

deploy() {
	certs
	adminSecret
	workload
	initDirectory
	caSecret
	idpInject
}

# List the users under ou=People (uid, mail). Uses LDAPS via the Service hostname (validating the certificate SAN) and binds as bob-svc,
# the same access path as Keycloak, so this also fails if the certificate or bind account has a problem; the output is empty when the directory has no users.
listUsers() {
	local pw
	pw=$(oc get secret $BIND_SECRET -n ibm-bob -o jsonpath='{.data.password}' | base64 -d)
	oc exec -n ibm-bob deploy/ds389 -c ds389 -- env LDAPTLS_CACERT=/data/tls/ca/ca.crt LDAPTLS_REQCERT=demand \
		ldapsearch -LLL -H "ldaps://ds389.ibm-bob.svc.cluster.local:636" -D "$BIND_DN" -w "$pw" -b "ou=People,${BASE_DN}" -s one uid mail
}

# Test TCP connectivity from the Keycloak pod to the 389ds LDAPS port (verifies Service DNS resolution and network policy)
testFromKeycloak() {
	oc exec -n ibm-bob bob-keycloak-0 -c keycloak -- bash -c \
		'timeout 5 bash -c "echo > /dev/tcp/ds389.ibm-bob.svc.cluster.local/636"' &&
		echo "# reachable from keycloak" || { echo "# unreachable from keycloak" >&2; return 1; }
}

# The list item to add to ldaps ("- " indented by 2 spaces, fields indented by 4 spaces, consistent with how configure-idp.sh parses it)
_idpItem() {
	cat <<EOF
  - name: ${IDP_NAME}
    vendor: rhds
    connectionUrl: ldaps://ds389.ibm-bob.svc.cluster.local:636
    usersDn: ou=People,${BASE_DN}
    usernameLDAPAttribute: uid
    rdnLDAPAttribute: uid
    uuidLDAPAttribute: nsUniqueId
    userObjectClasses: inetOrgPerson,organizationalPerson,person
    bindDn: ${BIND_DN}
    bindPasswordSecret:
      name: ${BIND_SECRET}
      key: password
    ldapsCACertSecret:
      name: ${CA_SECRET}
      key: ca.crt
    useTruststoreSpi: always
    userSync:
      enabled: true
EOF
}

# Only append one list item to ldaps in config-idp.yaml, leaving everything else untouched (template, comments, other items).
#   - An item named ${IDP_NAME} already exists:           skip
#   - No top-level ldaps: (still commented out):          exit with an error. Uncommenting is a manual task; the script does not do it
#   - No real list items under top-level ldaps::          the new item goes right after ldaps:, and the reference comment block follows it
#   - Real list items already exist under top-level ldaps: the new item is appended after the last item
# The new item must come before the reference comment block: configure-idp.sh treats a non-empty line at column 0 (including # comments) as the end of the ldaps block.
idpInject() {
	local file=${1:-$IDP_CONFIG} tmp
	if [ ! -f "$file" ]; then
		echo "# $file not found" >&2
		return 1
	fi
	if grep -qE "^  - name: ${IDP_NAME}[[:space:]]*$" "$file"; then
		echo "# ldaps item '${IDP_NAME}' exists in $file, skip"
		return
	fi
	if ! grep -qE '^ldaps:[[:space:]]*(#.*)?$' "$file"; then
		echo "# $file has no top-level 'ldaps:' (commented out?); uncomment it manually first, then re-run" >&2
		return 1
	fi
	tmp=$(mktemp)
	# Approach: the new item goes right after "ldaps:", and the reference comment block after it is left as is.
	# If ldaps already has real list items ("  - "), insert after the end of the last item so the items stay contiguous.
	ITEM="$(_idpItem)" awk '
		{ l[NR] = $0 }
		END {
			start = 0
			for (i = 1; i <= NR; i++) if (l[i] ~ /^ldaps:[ \t]*(#.*)?$/) { start = i; break }
			last = start
			for (i = start + 1; i <= NR; i++) {
				if (l[i] ~ /^[^ \t#]/) break
				if (l[i] ~ /^[ \t]/ && l[i] !~ /^[ \t]*(#.*)?$/) last = i
			}
			for (i = 1; i <= last; i++) print l[i]
			print ENVIRON["ITEM"]
			for (i = last + 1; i <= NR; i++) print l[i]
		}' "$file" >"$tmp"
	echo "# $file: appending ldaps item '${IDP_NAME}', changes:"
	diff -u "$file" "$tmp" || true
	cat "$tmp" >"$file"
	rm -f "$tmp"
}

status() {
	oc get pods,svc,pvc,certificate -n ibm-bob -l 'app=ds389' 2>&1
	oc get certificate,secret -n ibm-bob | grep -E "ds389|${BIND_SECRET}|${CA_SECRET}"
}

uninstall() {
	oc delete deploy/ds389 svc/ds389 -n ibm-bob --ignore-not-found
	oc delete certificate ds389-tls ds389-ca -n ibm-bob --ignore-not-found
	oc delete issuer ds389-ca-issuer ds389-selfsigned -n ibm-bob --ignore-not-found
	oc delete secret ds389-tls ds389-ca ds389-admin $BIND_SECRET $CA_SECRET -n ibm-bob --ignore-not-found
	echo "# To remove PVC ds389-data completely, run `oc delete pvc ds389-data -n ibm-bob`"
}

$@
