-- Compliance Copilot — database bootstrap
-- Run once against your target Postgres (Supabase SQL editor or psql):
--     psql "$PG_URL" -f scripts/init_db.sql

CREATE EXTENSION IF NOT EXISTS vector;

-- Regulatory chunks (read by backend/check_compliance.py and written by
-- backend/embed.py). Embedding dimension matches Ollama's nomic-embed-text.
CREATE TABLE IF NOT EXISTS law_chunks (
    id SERIAL PRIMARY KEY,
    document_id TEXT,
    text TEXT NOT NULL,
    metadata JSONB,
    embedding VECTOR(768)
);

CREATE INDEX IF NOT EXISTS law_chunks_embedding_idx
    ON law_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS law_chunks_category_idx
    ON law_chunks ((metadata->>'category'));

-- Reports table (frontend reads this; backend writes uploads here)
CREATE TABLE IF NOT EXISTS reports (
    id BIGSERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    file_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    claims JSONB,
    ingredients JSONB,
    compliance JSONB,
    compliance_score INTEGER,
    issue_counts JSONB,
    recent_issues JSONB
);
