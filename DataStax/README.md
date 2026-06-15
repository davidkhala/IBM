ports
- `7000`: intra-node communication (insecure)
- `7001`: intra-node communication
- `7199`: JMX (for Ops)
- `9042`: CQL protocol
- `8983`: Solr API
- `7077`: Spark Master
- `7080`: Spark Web UI
- `7081`: Spark Worker UI
- `4040`: Spark Application UI
- `8182`: Gremlin
- `61620`: OpsCenter agent
- `8888`: OpsCenter UI
# SDK
python
- [for AstraDB](https://github.com/davidkhala/py-databases/tree/main/davidkhala/data/base/astra)


# [Run a DSE container](https://docs.datastax.com/en/dse/6.9/installing/docker.html)
[DSE server](https://hub.docker.com/r/datastax/dse-server)
- A single DSE node
- Cassandra File System (CFS) isn’t supported in containers.
- The JVM heap size must be set for DSE running inside the container. If not set, Java does not honor resource limits set for the container, and will peer through the container to use resources (memory and CPU) of the host. 
- minimum 4GB memory 

[Data API](https://hub.docker.com/r/stargateio/data-api)
- An API that you can use to interact with DSE as an alternative to Cassandra drivers.

[DataStax Studio](https://hub.docker.com/r/datastax/dse-studio)
- A developer tool for sending Cassandra Query Language (CQL), DSE Graph, and Gremlin Query Language queries in notebook format.

[OpsCenter](https://hub.docker.com/r/datastax/dse-opscenter)
- A web-based visual management and monitoring solution for DSE.
- Lifecycle Manager (LCM) isn’t supported in containers.


## My
On GCP Cloud Run
- https://dse-server-111562655547.asia-east2.run.app:9042
