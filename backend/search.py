import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from openai import OpenAI
from dotenv import load_dotenv
from backend.config import get_connection

# 1. Load OpenAI API Key
load_dotenv
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 2. Embed the user's question
def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

# 3. Search for top-k most similar chunks
def search_similar_chunks(query, top_k=3):
    query_embedding = get_embedding(query)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT content, embedding <#> %s::vector AS distance
        FROM chunks
        ORDER BY distance ASC
        LIMIT %s;
        """,
        (query_embedding, top_k)
    )

    results = cur.fetchall()
    cur.close()
    conn.close()

    return results


if __name__ == "__main__":
    user_query = input("🔍 Ask a question: ")
    results = search_similar_chunks(user_query)

    for i, (chunk, score) in enumerate(results):
        print(f"\n--- Result {i+1} (score={score:.4f}) ---\n{chunk[:500]}")