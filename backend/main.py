"""
Compliance Copilot — FastAPI entry point.

Run locally:
    uvicorn backend.main:app --reload --port 8000

Run in Docker:
    See docker-compose.yml.
"""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env before any submodule imports it
load_dotenv()

from backend.api import extraction, compliance  # noqa: E402

app = FastAPI(
    title="Compliance Copilot API",
    description="Extract ingredients & claims from product labels, then run multi-jurisdiction compliance analysis powered by local Ollama + pgvector.",
    version="0.2.0",
)

# CORS: allow the Next.js dev server plus any extra origins from env
_extra_origins = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", *_extra_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extraction.router)
app.include_router(compliance.router)


@app.get("/")
def root():
    return {
        "service": "compliance-copilot",
        "version": app.version,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
