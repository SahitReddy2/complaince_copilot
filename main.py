from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import extraction  # adjust path if needed

app = FastAPI(
    title="LabelLens Extractor API",
    description="API for extracting ingredients, claims, and compliance data from cosmetic product files.",
    version="0.1.0"
)

# Enable CORS for frontend (localhost:3000 for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include only the extraction router for now
app.include_router(extraction.router)
