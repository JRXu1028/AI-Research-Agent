# RAG Implementation

当前 RAG 实现从简，只保留本地 Chroma 向量库。

## Stack

```text
Embedding: sentence-transformers/all-MiniLM-L6-v2
Vector DB: Chroma
Storage: data/chroma_db
Tool: knowledge_search
```

## Flow

```text
user query
  -> embedding
  -> Chroma similarity_search_with_score
  -> top-k documents
  -> knowledge_search tool result
  -> Qwen final answer
```

## Core Files

```text
src/embeddings.py      # create embedding model
src/vector_store.py    # Chroma wrapper
src/knowledge_base.py  # built-in documents
src/rag.py             # global RAG system
src/tools.py           # knowledge_search tool
```

## Rebuild Index

Delete local Chroma data and restart:

```bash
rm -rf data/chroma_db
python app.py
```

Or call:

```python
initialize_rag_system(force_reload=True)
```
