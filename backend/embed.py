# backend/embed.py

import os
import json
from openai import OpenAI
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
from backend.config import get_connection
from backend.chunk import chunk_text

# 1. Load API Key
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 2. Input directory
CHUNK_DIR = "data/chunks"

# 3. Connect to Postgres and create table
def create_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS chunks;")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id SERIAL PRIMARY KEY,
            content TEXT,
            embedding VECTOR(1536),
            chunk_index INTEGER,
            category TEXT,
            source_type TEXT,
            source_path TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Table 'chunks' ready.")

# 4. Embed text using OpenAI
def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

# 5. Load all JSON files and insert chunks
def embed_all_json():
    conn = get_connection()
    cur = conn.cursor()

    for fname in os.listdir(CHUNK_DIR):
        if not fname.endswith(".json"):
            continue

        path = os.path.join(CHUNK_DIR, fname)
        print(f"📦 Embedding chunks from {fname}")
        
        with open(path, "r", encoding="utf-8") as f:
            chunks = json.load(f)  # This is a list

        for item in chunks:
            text = item.get("chunk", "")
            metadata = item.get("metadata", {})
            source = metadata.get("source", "")
            doc_type = metadata.get("type", "")
            category = metadata.get("category", "")

            embedding = get_embedding(text)

            cur.execute(
    """
    INSERT INTO chunks (content, embedding, chunk_index, category, source_type, source_path)
    VALUES (%s, %s, %s, %s, %s, %s);
    """,
    (text, embedding, item.get("chunk_index", 0), category, doc_type, source)
)


    conn.commit()
    cur.close()
    conn.close()
    print("✅ All chunks embedded and stored.")


# 6. Run
if __name__ == "__main__":
    create_table()
    embed_all_json()
