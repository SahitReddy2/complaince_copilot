"""
Embed chunked regulatory documents into the law_chunks pgvector table.

Reads pre-chunked JSON files from data/chunks/, embeds each chunk with the
local Ollama nomic-embed-text model (768-dim), and stores the result in the
law_chunks table. The schema matches what backend/check_compliance.py expects.

Usage:
    python -m backend.embed                # embed everything in data/chunks/
    python -m backend.embed --recreate     # drop and recreate the table first
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

from backend.config import get_connection

load_dotenv()
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

CHUNK_DIR = "data/chunks"
EMBEDDING_MODEL = "nomic-embed-text"
EMBEDDING_DIM = 768


def create_table(recreate: bool = False) -> None:
    """Create the law_chunks table (and pgvector extension) if missing."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    if recreate:
        cur.execute("DROP TABLE IF EXISTS law_chunks;")
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS law_chunks (
            id SERIAL PRIMARY KEY,
            document_id TEXT,
            text TEXT NOT NULL,
            metadata JSONB,
            embedding VECTOR({EMBEDDING_DIM})
        );
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS law_chunks_embedding_idx
        ON law_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """
    )
    conn.commit()
    cur.close()
    conn.close()
    print("Table 'law_chunks' ready.")


def get_embedding(text: str) -> list:
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


def embed_all_json() -> None:
    if not os.path.isdir(CHUNK_DIR):
        print(f"Chunk directory not found: {CHUNK_DIR}", file=sys.stderr)
        sys.exit(1)

    conn = get_connection()
    cur = conn.cursor()

    total = 0
    for fname in os.listdir(CHUNK_DIR):
        if not fname.endswith(".json"):
            continue

        path = os.path.join(CHUNK_DIR, fname)
        print(f"Embedding chunks from {fname}")

        with open(path, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        for item in chunks:
            text = item.get("chunk", "")
            if not text.strip():
                continue
            metadata = item.get("metadata", {}) or {}
            document_id = metadata.get("source") or fname

            embedding = get_embedding(text)
            cur.execute(
                """
                INSERT INTO law_chunks (document_id, text, metadata, embedding)
                VALUES (%s, %s, %s, %s);
                """,
                (document_id, text, json.dumps(metadata), embedding),
            )
            total += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"Embedded {total} chunks into law_chunks.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recreate", action="store_true", help="Drop and recreate law_chunks before embedding.")
    args = parser.parse_args()

    create_table(recreate=args.recreate)
    embed_all_json()


if __name__ == "__main__":
    main()
