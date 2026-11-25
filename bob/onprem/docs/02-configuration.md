# 02 — Configuration

Three kinds of configuration files need to be prepared:

| File | Required | Purpose |
| ---- | -------- | ------- |
| `config.yaml` | Yes | Namespace, storage classes, image registry, add-ons, model secrets |
| `config-model-gateway.yaml` | Yes | LLM endpoint definitions; |
| `config-idp.yaml` | No | LDAP/AD federation, can be generated |

## config.yaml

Configure `global.fileStorageClass` and `global.blockStorageClass`
- View the current storage classes by `oc get storageclass`
- Supported storage classes
  - `ocs-storagecluster-cephfs`: OpenShift Data Foundation (ODF)
  - `managed-nfs-storage`: Managed NFS
  - `crc-csi-hostpath-provisioner`: CRC default

## config-model-gateway.yaml
See in [Configuring the Model Gateway](https://bob.ibm.com/docs/ide/enterprise/on-premises/model-gateway/configuration).


Supported model providers:
- AWS Bedrock
- Azure OpenAI
- GCP Gemini Platform (vertex).


Rules:

- `models` must contain three reserved names: `premium-ide` (default model for LLM chat), `security` (guardrail), and `background` (background tasks).
- Secrets are referenced from `env.<VAR>`; the variable values are set under `bob.modelGateway.secrets` in `config.yaml`.
- Set `supports_vision` to `true` only if the model actually supports images.

> It is recommended to use smaller models (such as `openai/gpt-oss-20b`) for `security` / `background`.

## config-idp.yaml
It will be used by `admin.sh configureIdp`
- ldap entry can be autogen by ldap.sh
