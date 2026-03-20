# Prompt Lab

Asset type: when you Save your work

- Prompt template: Save the current prompt only, without its history.
- Prompt session: Save history and data from the current session.
  - 
- Standard notebook

UI

- Chat
- Structured
- Freeform: not a chat interface
  - yet another form of Structured

# Ground gen AI with vectorized documents

Vector stores types

## In memory: attachment along with chat
embeddings model
- ibm/granite-embedding-278m-multilingual (default)
- granite-embedding-278m-multilingual
- slate-125m-english-rtrvr-v2
- slate-30m-english-rtrvr-v2
- multilingual-e5-large
- all-minilm6-v2

attachment size limit  
- 300MB .pptx
- 50MB .docx
- 50MB .pdf
- 5MB .txt

Not In memory: your attachment will be copied to bucket as-is.
Not OCR: Attach file come along with **vector index** provision
- Too much vector index, better to group files into fewer indexes.


search settings
- Reranking model: ms-marco-minilm-l-12-v2
- Top K: range [1, 50], default is 3
- Top N: range [1, 3]
  - in dify：Top N == Top K

## watsonx.data Milvus
## Elasticsearch
