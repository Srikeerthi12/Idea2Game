"""
api/main.py
-----------
FastAPI application entry point.

Run with:
    uvicorn api.main:app --reload --port 8080

Endpoints:
    POST /generate          — start a game generation job
    GET  /jobs/{job_id}     — poll job status + live progress
    GET  /history           — last 20 generated games (Supabase)
    GET  /history/{id}      — single run by UUID
    DELETE /history/{id}    — delete a run
    POST /history/play/{id} — launch game natively
    POST /similar           — semantic game search (ChromaDB)
    GET  /health            — health check
"""

import os
import sys
from pathlib import Path

# ── Force UTF-8 on Windows (fixes charmap codec errors from emoji in logs) ──
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ── Load .env before anything else ────────────────────────────────
def _load_env():
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            sep = "=" if "=" in line else ":"
            k, _, v = line.partition(sep)
            os.environ.setdefault(k.strip(), v.strip())

_load_env()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.generate import router as generate_router
from api.routes.history  import router as history_router

# ── App ───────────────────────────────────────────────────────────
app = FastAPI(
    title       = "IdeaToGame API",
    description = "Multi-agent AI pipeline that turns ideas into Pygame games",
    version     = "2.0.0",
)

# ── CORS — allow React dev server (port 5173) ─────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:5173", "http://localhost:3000"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Routers ───────────────────────────────────────────────────────
app.include_router(generate_router, tags=["Generation"])
app.include_router(history_router,  tags=["History"])


# ── Health check ──────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": "2.0.0"}
