# Connectivity


## Platform connections
> Connections in the Platform assets catalog.
- It is for data service (DataStage, Data Virtualization) 
- These connections can be accessed by all users
- By default, it has a Connector named `IBM Cloud Connection`
  - Type: `IBM Cloud`


## Data source definitions (DSD)
> A data source definition is an asset that functions as a unique stable identifier that uses a set of endpoints to identify a single data source instance.
- It is used for data governance (catalog, lineage, policy)
  - It does not include credential, test run

By default, it has an `IBM Cloud` connection
- Data source type: `IBM Cloud`
- It is assigned to Connector `IBM Cloud Connection`
