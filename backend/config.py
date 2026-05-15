"""
Centralised runtime configuration: database connection + Ollama client factory.

All modules should import from here rather than reading env vars directly,
so we have one source of truth for connection details.
"""

import os

import psycopg2
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ── Database (Postgres / Supabase) ────────────────────────────────────────
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "postgres")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")
PG_SSLMODE = os.getenv("PG_SSLMODE", "prefer")  # 'require' for Supabase

# ── Ollama (local LLM) ────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen2:7b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def get_connection():
    """Return a new psycopg2 connection using the configured PG_* env vars."""
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
        sslmode=PG_SSLMODE,
    )


def get_ollama_client() -> OpenAI:
    """Return an OpenAI-compatible client pointed at the local Ollama server."""
    return OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
