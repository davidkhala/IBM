# watsonx.data

> Design a data architecture to deliver high-quality, trusted data products that are ready for AI.
- aka. Data Fabric, dataplatform.cloud.ibm.com


# Design
- query layer, connectors are conceptually derived from PrestoSQL
- data format: iceberg
- Job engine: Spark (v3.4)
## Driver manager
The Driver Manager within the Configurations section of IBM watsonx.data provides the functionality to add external JDBC drivers (in .jar file format) required for connecting to - HANA (using ngdbc 2.17.12)
- MySQL (using mysql-connector/j 8.2.0)
- without compatibility: only driver version exactly equals to specified are allowed.
