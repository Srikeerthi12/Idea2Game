"""
api/routes/history.py
---------------------
GET  /history           — last 20 runs from Supabase
GET  /history/{run_id}  — single run by UUID
DELETE /history/{run_id} — delete a run
POST /history/play/{run_id} — launch game natively
POST /similar           — semantic search in ChromaDB
"""

import tempfile
import subprocess
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException

from api.models import HistoryItem, SimilarRequest, SimilarResponse
from memory.db import get_run_by_id, get_run_history, delete_run
from memory.vector_store import search_similar

router = APIRouter()


@router.get("/history", response_model=list[HistoryItem])
async def list_history(limit: int = 20):
    """Return the most recent runs, newest first."""
    rows = get_run_history(limit=limit)
    return [
        HistoryItem(
            id          = row.get("id", ""),
            game_idea   = row.get("game_idea", ""),
            output_file = row.get("output_file", ""),
            status      = row.get("status", ""),
            retries     = row.get("retries", 0),
            description = row.get("description", ""),
            code_length = row.get("code_length", 0),
            created_at  = str(row.get("created_at", "")),
        )
        for row in rows
    ]


@router.get("/history/{run_id}")
async def get_history_item(run_id: str):
    """Fetch a single run record by UUID, including the game code."""
    row = get_run_by_id(run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "id":          row.get("id", ""),
        "game_idea":   row.get("game_idea", ""),
        "output_file": row.get("output_file", ""),
        "status":      row.get("status", ""),
        "retries":     row.get("retries", 0),
        "description": row.get("description", ""),
        "code_length": row.get("code_length", 0),
        "created_at":  str(row.get("created_at", "")),
        "game_code":   row.get("game_code", ""),
    }

@router.delete("/history/{run_id}")
async def delete_history_item(run_id: str):
    """Delete a run record from Supabase."""
    success = delete_run(run_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete run")
    return {"status": "success", "message": "Run deleted"}

@router.post("/history/play/{run_id}")
async def play_game(run_id: str):
    """Launch the game natively by fetching code from Supabase."""
    row = get_run_by_id(run_id)
    if not row or not row.get("game_code"):
        raise HTTPException(status_code=404, detail="Game code not found")
        
    code = row.get("game_code", "")
    output_file = row.get("output_file", "game.py")
    
    project_root = Path(__file__).parent.parent.parent
    temp_file = project_root / f".temp_{output_file}"
    
    try:
        temp_file.write_text(code, encoding="utf-8")
        # Launch asynchronously
        subprocess.Popen([sys.executable, str(temp_file)], cwd=str(project_root))
        return {"status": "success", "message": "Game launched"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/similar", response_model=SimilarResponse)
async def find_similar(request: SimilarRequest):
    """Semantic search for past games similar to the given idea."""
    results = search_similar(request.game_idea, k=request.k)
    return SimilarResponse(results=results or "No similar games found yet.")
