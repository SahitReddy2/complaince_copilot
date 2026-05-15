# Compliance Copilot — Setup Guide

End-to-end setup for the FastAPI backend + Next.js frontend + Ollama LLM + Supabase Postgres.

## Architecture

```
┌────────────────┐    HTTP     ┌────────────────┐    psycopg2    ┌──────────────┐
│  Next.js (3000)│ ──────────▶ │ FastAPI (8000) │ ─────────────▶ │  Supabase    │
│   label-lens-ai│             │    backend/    │                │  (pgvector)  │
└────────────────┘             └────────┬───────┘                └──────────────┘
        │                               │
        │  storage + reports table       │  OpenAI-compatible API
        ▼                               ▼
┌────────────────┐             ┌────────────────┐
│  Supabase JS   │             │ Ollama (11434) │
└────────────────┘             │  qwen2:7b      │
                               │  nomic-embed   │
                               └────────────────┘
```

## Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- **Ollama** running locally — https://ollama.com/download
- **Supabase project** (free tier is fine) — https://supabase.com
- **Tesseract OCR** for image extraction — https://github.com/UB-Mannheim/tesseract/wiki

## 1. Pull Ollama models

```powershell
ollama pull qwen2:7b
ollama pull nomic-embed-text
```

Verify Ollama is reachable:

```powershell
curl http://localhost:11434/api/tags
```

## 2. Set up Supabase

In your Supabase project's SQL editor, run:

```sql
-- From scripts/init_db.sql
\i scripts/init_db.sql
```

Or paste the contents of `scripts/init_db.sql` directly. This:

- Enables the `vector` extension (pgvector)
- Creates `law_chunks` (used for RAG)
- Creates `reports` (used by the upload flow)

Then grab two things from **Project Settings → API**:

- `Project URL` → `SUPABASE_URL`
- `service_role` key → `SUPABASE_SERVICE_KEY` (server-side only, keep secret)
- `anon` key → `NEXT_PUBLIC_SUPABASE_ANON_KEY` (browser-side OK)

And from **Project Settings → Database → Connection info**:

- Host → `PG_HOST` (e.g. `db.xxxx.supabase.co`)
- Port → `PG_PORT` (5432)
- Database name → `PG_DB` (`postgres`)
- User → `PG_USER` (`postgres`)
- Password → `PG_PASSWORD`

## 3. Configure environment

**Backend** — copy and fill in:

```powershell
copy .env.example .env
# Edit .env, set PG_SSLMODE=require for Supabase
```

**Frontend** — copy and fill in:

```powershell
copy label-lens-ai\.env.local.example label-lens-ai\.env.local
# Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY
```

## 4. Install dependencies

**Backend:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

**Frontend:**

```powershell
cd label-lens-ai
npm install
cd ..
```

## 5. Ingest regulatory documents

Chunked law PDFs live in `data/chunks/` as JSON. To embed them into `law_chunks`:

```powershell
python -m backend.embed --recreate
```

Use `--recreate` the first time (drops and recreates the table). Subsequent runs without `--recreate` append.

## 6. Run the stack

**Option A — Local dev (recommended for iterating):**

Terminal 1 (backend):

```powershell
uvicorn backend.main:app --reload --port 8000
```

Terminal 2 (frontend):

```powershell
cd label-lens-ai
npm run dev
```

Open http://localhost:3000.
API docs at http://localhost:8000/docs.

**Option B — Docker Compose:**

```powershell
docker compose up --build
```

The backend container reaches Ollama on the host via `host.docker.internal:11434`.

## 7. Smoke test

Backend health:

```powershell
curl http://localhost:8000/health
```

Compliance check (cosmetics, US only):

```powershell
python -m backend.check_compliance '{"industry":"cosmetics","ingredients":["benzene","glycerin"],"jurisdictions":["US"]}'
```

Should return a JSON object with `non_compliant` findings and a `by_jurisdiction` breakdown.

## Switching industries

The compliance engine is industry-agnostic. Available configs in `config/industries/`:

- `cosmetics.yaml`
- `food.yaml`
- `supplements.yaml`
- `pharma_otc.yaml`

Pass `industry` in the JSON payload to `check_compliance` or as a query param to `/api/extract/analyze-document`. To add a new industry, drop a new YAML and ingest the relevant law texts with a matching `category` tag.

## Switching the LLM

`.env` lets you swap models without code changes:

```
OLLAMA_CHAT_MODEL=mistral:7b-instruct
OLLAMA_EMBED_MODEL=nomic-embed-text
```

If you change `OLLAMA_EMBED_MODEL` to one with different dimensionality, edit `EMBEDDING_DIM` in `backend/embed.py` and re-run `--recreate`.

## Troubleshooting

- **`relation "law_chunks" does not exist`** — Run `scripts/init_db.sql` against your Postgres.
- **Compliance returns "No relevant regulatory content found"** — You haven't run `python -m backend.embed` yet, or the `metadata->>'category'` of your chunks doesn't match the industry config.
- **Ollama timeouts** — `qwen2:7b` needs ~5GB RAM. Try `mistral:7b-instruct` or `phi3:mini` on lighter hardware.
- **Frontend 500s on upload** — Check the backend terminal; likely a missing env var (`SUPABASE_SERVICE_KEY`) or Supabase storage bucket `reports` doesn't exist. Create it in Supabase → Storage.
