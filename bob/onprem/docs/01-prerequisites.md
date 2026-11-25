# 01 — Prerequisites


DNS and certificate policy
- Decide whether to use an public root CA certificate or the default self-signed CA (`CN=Bob Internal CA`). This can be configured after installation; see [post-install.md](./04-post-install.md).


## Hardware requirement
- Bob self-hosted requests about 10.8 vCPU / 10.8 GiB / ~24 GiB PV;
- Insufficient storage throughput or I/O performance, particularly for PostgreSQL workloads, can result in increased response times, slower indexing operations, and degraded overall system performance. 

### Official reference topology

[Source](https://bob.ibm.com/docs/ide/enterprise/on-premises/system-requirements#minimum-reference-configuration)

| Node role |	Count	| CPU per node | Memory per node | Storage | 	
| Control plane | 3	| 4 vCPU (minimum)|	16 GiB (minimum)|	50 GiB |
| Infrastructure nodes | 	3	|~4 vCPU	|~16 GiB	| 50 GiB |
| Worker nodes | 	3	| 8 vCPU |	16 GiB	| 200 GiB |

### CRC reference specs
12 CPU, 16 GiB, 100  GiB (without RAG)


## software dependencies
Workstation bin tool check:`./preinstall.sh binCheck`


### Download and extract the release package

Download `ibm-bob-install-<version>.tar.gz` from the Releases of the [IBM Bob GitHub repository](https://github.com/IBM/ibm-bob), place it in this directory (`bob/onprem/`), and then extract it:

Release package structure:

```
|- /bin
|- /charts
|- /etc
|- logs
README.md
bobctl
...
```

### OpenShift access and permissions

1. Log in
  ```
  # Requires `cluster-admin` (or equivalent RBAC).
  oc login <api-server> --token=<cluster-admin-token> 
  ```
2. Verify openshift
  ```
  ./preinstall.sh ocCheck
  ```
#### Install cert-manager
On startup, `bobctl install` checks for the cert-manager CRDs and aborts immediately if they are missing.
  

> On ROKS on IBM Cloud: if, in the cluster's Overview panel in IBM Cloud, the `Networking` section > `Outbound traffic protection enabled` setting was enabled at provisioning, the catalog sources become unreachable because of `disableAllDefaultSources: true`.
> - solution: `oc patch operatorhub cluster --type merge -p '{"spec":{"disableAllDefaultSources":false}}'`

1. install
  - via Openshift Console: In *Ecosystem* > *Software Catalog*, install **cert-manager Operator for Red Hat OpenShift**
    - Select channel `stable-v1`
  - via CLI: `./admin.sh installCertman`
2. Verify cert-manager:`./admin.sh certmanStatus`

