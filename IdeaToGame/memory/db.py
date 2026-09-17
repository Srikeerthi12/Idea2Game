"""
memory/db.py
------------
Supabase client for logging every pipeline run as metadata.

Stores: idea, output file, status, retries, token estimate, timestamp.
Used by the FastAPI /history endpoint (Phase 4) and for analytics.

Setup (one-time in Supabase dashboard):
    Run the SQL in schema.sql to create the `runs` table.
"""

import os
import uuid
from datetime import datetime, timezone

from typing import Optional

from supabase import Client, create_client

# ---------------------------------------------------------------------------
# Lazy Supabase client
# ---------------------------------------------------------------------------
_supabase: Optional[Client] = None


def _get_client() -> Client:
    """Lazily initialise the Supabase client."""
    global _supabase
    if _supabase is None:
        url = os.environ.get("SUPABASE_URL", "").strip()
        key = os.environ.get("SUPABASE_ANON_KEY", "").strip()

        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env.\n"
                "Get these from: https://supabase.com/dashboard → Project Settings → API"
            )

        _supabase = create_client(url, key)
    return _supabase


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def log_run(
    game_idea: str,
    output_file: str,
    status: str,
    retries: int = 0,
    description: str = "",
    code_length: int = 0,
    game_code: str = "",
) -> str:
    """
    Insert a run record into the Supabase `runs` table.

    Returns the generated run_id (UUID string) so it can be passed
    to ChromaDB for cross-referencing.

    Fails silently with a warning if Supabase is unreachable —
    the pipeline should not crash just because logging failed.
    """
    run_id = str(uuid.uuid4())

    try:
        client = _get_client()
        client.table("runs").insert({
            "id":          run_id,
            "game_idea":   game_idea,
            "output_file": output_file,
            "status":      status,          # "success" | "failed" | "retrying"
            "retries":     retries,
            "description": description,
            "code_length": code_length,     # chars — rough token proxy
            "game_code":   game_code,       # raw python code
            "created_at":  datetime.now(timezone.utc).isoformat(),
        }).execute()

        print(f"[Supabase] Run logged (id={run_id}, status={status}).")

    except Exception as exc:
        print(f"[Supabase] WARNING: Could not log run — {exc}")

    return run_id


def get_run_history(limit: int = 20) -> list[dict]:
    """
    Fetch the most recent runs from Supabase, newest first.
    Returns an empty list if Supabase is unreachable.
    """
    try:
        client = _get_client()
        response = (
            client.table("runs")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    except Exception as exc:
        print(f"[Supabase] WARNING: Could not fetch history — {exc}")
        return []


def get_run_by_id(run_id: str) -> Optional[dict]:
    """Fetch a single run record by its UUID."""
    try:
        client = _get_client()
        response = (
            client.table("runs")
            .select("*")
            .eq("id", run_id)
            .single()
            .execute()
        )
        return response.data
    except Exception as exc:
        print(f"[Supabase] WARNING: Could not fetch run {run_id} — {exc}")
        return None

def delete_run(run_id: str) -> bool:
    """Delete a single run record by its UUID."""
    try:
        client = _get_client()
        client.table("runs").delete().eq("id", run_id).execute()
        return True
    except Exception as exc:
        print(f"[Supabase] WARNING: Could not delete run {run_id} — {exc}")
        return False
