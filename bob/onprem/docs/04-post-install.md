# 05 — Post-installation tasks

## Connect Bob clients (IDE/CLI)

[Accessing Bob self-hosted](https://bob.ibm.com/docs/ide/enterprise/on-premises/accessing).


### 1. Root CA certificate

Bob clients cannot connect until the certificate is trusted.


```bash
# Determine the certificate mode:
oc get secret bob-external-tls -n ibm-bob -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -issuer
```
- If the issuer is `CN=Bob Internal CA`, the default self-signed certificate is in use.


#### Public Root certificate (recommended)

0. Certificate requirements
  - Unencrypted private key
  - Includes the full certificate chain
  - PEM format
  - SAN covers all hostnames; the hostnames can be obtained with `./ca.sh getIngressHosts`
1. Create the Secret and apply it:

   ```bash
   oc create secret generic my-tls-secret \
     --from-file=tls.crt=tls.crt \
     --from-file=tls.key=tls.key \
     --from-file=ca.crt=ca.crt \
     -n ibm-bob

   ./bobctl setup-route --tls-secret my-tls-secret
   ```

   For publicly trusted certificates you can use `oc create secret tls my-tls-secret --cert=... --key=... -n ibm-bob`. To update an existing Secret, append `| oc apply -f -` after `oc create ... --dry-run=client -o yaml`.



To revoke the TLS certificate and return to IBM Bob's default self-signed certificate:
```
./bobctl reset-route
```

#### Default self-signed certificate

The self-signed certificate is issued by cert-manager.

1. Export the Root CA cert:
  ```bash
  ./client.sh getSelfSignedRootCA
  ```
2. Import the Root CA cert into the operating system trust store.
  - debian: `./client.sh debian-trust-ca`



### 2. Configure the Bob client
Configure Bob IDE
1. Run `./client.sh ide`, 
2. Restart Bob IDE

Configure Bob Shell
- Run `./client.sh shell`, 

