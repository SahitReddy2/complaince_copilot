# backend/scripts/chunk.py
import os
import json
from textwrap import wrap

# Config
INPUT_DIR = "data/extracted"
CHUNK_DIR = "data/chunks"
CHUNK_SIZE = 500  # words per chunk

os.makedirs(CHUNK_DIR, exist_ok=True)


def chunk_text(text, size=CHUNK_SIZE):
    words = text.split()
    return [' '.join(words[i:i + size]) for i in range(0, len(words), size)]


def process_file(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    text = data["text"]
    base_meta = {k: v for k, v in data.items() if k != "text"}

    chunks = chunk_text(text)

    return [
        {
            "chunk": chunk,
            "chunk_index": i,
            **base_meta
        }
        for i, chunk in enumerate(chunks)
    ]


def chunk_all():
    for fname in os.listdir(INPUT_DIR):
        if not fname.endswith(".json"):
            continue

        path = os.path.join(INPUT_DIR, fname)
        print(f"🔪 Chunking {fname}...")
        chunks = process_file(path)

        out_path = os.path.join(CHUNK_DIR, fname)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved {len(chunks)} chunks to {out_path}")


if __name__ == "__main__":
    chunk_all()
