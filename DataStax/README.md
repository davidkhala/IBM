# [Run a DSE container](https://docs.datastax.com/en/dse/6.9/installing/docker.html)
[DSE server](https://hub.docker.com/r/datastax/dse-server)
- A single DSE node
- Cassandra File System (CFS) isn’t supported in containers.
- The JVM heap size must be set for DSE running inside the container. If not set, Java does not honor resource limits set for the container, and will peer through the container to use resources (memory and CPU) of the host. 

[Data API](https://hub.docker.com/r/stargateio/data-api)
- An API that you can use to interact with DSE as an alternative to Cassandra drivers.

[DataStax Studio](https://hub.docker.com/r/datastax/dse-studio)
- A developer tool for sending Cassandra Query Language (CQL), DSE Graph, and Gremlin Query Language queries in notebook format.

[OpsCenter](https://hub.docker.com/r/datastax/dse-opscenter)
- A web-based visual management and monitoring solution for DSE.
- Lifecycle Manager (LCM) isn’t supported in containers.
