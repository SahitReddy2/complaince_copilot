"""
ingest_mocra.py
─────────────────────────────────────────────────────────────────────────
Turn MoCRA.txt (plain-text version of the Modernization of Cosmetics
Regulation Act of 2022) into a searchable vector index for Retrieval–
Augmented Generation (RAG).

• Reads `law_docs/text/MoCRA.txt`
• Splits into ~1 KB overlapping chunks
• Embeds each chunk with OpenAI’s `text-embedding-3-small`
• Stores vectors in a pgvector table  ➜  production-ready
  – or falls back to a local file-based index if Postgres isn’t set up
• Persists storage metadata so you can reload the index fast at runtime
"""

import os, re
from pathlib import Path
from llama_index import (
    SimpleDirectoryReader, VectorStoreIndex,
    ServiceContext, StorageContext, set_global_service_context
)
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.node_parser import SentenceSplitter

# ────────────────────────── 0.  Config ────────────────────────────────
# ❶  OpenAI API key (env var is safest; hard-code only for quick local test)
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY") or "sk-..."

# ❷  Paths
DOC_DIR      = Path("law_docs/text")
PERSIST_DIR  = Path("storage")        # for file-based metadata

# ────────────────────────── 1.  Load MoCRA ────────────────────────────
docs = SimpleDirectoryReader(
    DOC_DIR,
    required_exts=[".txt"],   # only text files
).load_data()

# quick sanity: keep only MoCRA if other files are present
docs = [d for d in docs if "mocra" in d.metadata["file_name"].lower()]

# ────────────────────────── 2.  Clean text ────────────────────────────
for d in docs:
    # strip “Page X / Y” artifacts
    d.text = re.sub(r"Page +\d+ +/ +\d+", "", d.text)

# ────────────────────────── 3.  Chunking settings ─────────────────────
parser = SentenceSplitter(
    chunk_size=1024,         # tokens ≈ characters for plain English
    chunk_overlap=128,
    respect_sentence_boundary=True,
)

# ────────────────────────── 4.  Choose vector store ───────────────────
USE_POSTGRES = True   # flip to False to keep everything local

if USE_POSTGRES:
    from llama_index.vector_stores.pgvector import PGVectorStore
    pg_store = PGVectorStore.from_params(         # adjust credentials ↓
        database="compliance",
        host="localhost",
        port="5432",
        user="postgres",
        password="postgres",
        table_name="mocra_embeddings",
    )
    storage_ctx = StorageContext.from_defaults(vector_store=pg_store)
else:
    storage_ctx = StorageContext.from_defaults(persist_dir=PERSIST_DIR)

# ────────────────────────── 5.  Service context ───────────────────────
service_ctx = ServiceContext.from_defaults(
    embed_model=OpenAIEmbedding(model="text-embedding-3-small")
)
set_global_service_context(service_ctx)

# ────────────────────────── 6.  Build & persist index ─────────────────
index = VectorStoreIndex.from_documents(
    docs,
    node_parser=parser,
    storage_context=storage_ctx,
)
index.storage_context.persist()   # saves manifest or commits to Postgres
print("✅  MoCRA vector index built and saved")

# ────────────────────────── 7.  Quick smoke test (optional) ───────────
if __name__ == "__main__":
    from llama_index.query_engine import RetrieverQueryEngine
    qe = RetrieverQueryEngine.from_index(index)
    print("\nTest query:")
    print(qe.query("When must cosmetic facilities renew registration?"))
