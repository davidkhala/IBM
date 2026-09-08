# IBM watsonx Orchestrate


## Discover agents in catalog
Start with a template


limit:
- no GitHub template. GitLab only
- no Healthcare, Investment, Research, Talent management templates found



# Agent Development Kit (ADK)
a set of tools designed to build and deploy agents using IBM watsonx Orchestrate.
- It is packaged as a Python library and command-line tool that enables builders to configure agents running on the IBM
WatsonX Orchestrate platform. 
- The ADK also supports the integration of agents and tools built on other frameworks.
- [source](https://github.com/IBM/ibm-watsonx-orchestrate-adk)
- [pypi](https://pypi.org/project/ibm-watsonx-orchestrate)
  - aka. IBM watsonx.orchestrate SDK
## command-line binary `orchestrate`
Install by `uv tool install ibm-watsonx-orchestrate`

config
- `~/.config/orchestrate/config.yaml`: 环境列表和active_environment
- `~/.cache/orchestrate/credentials.yaml`: credentials for current active_environment
  - `apikey`
  - `wxo_mcsp_token`: cached IAM token, 1 hour expiry, auto refresh

