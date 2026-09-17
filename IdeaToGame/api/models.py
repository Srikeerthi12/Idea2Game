"""
api/models.py
-------------
Pydantic schemas for all FastAPI request and response bodies.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# /generate
# ---------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    game_idea:   str = Field(..., description="Plain-English game idea")
    output_file: str = Field("game.py", description="Filename to save generated code to")


class GenerateResponse(BaseModel):
    job_id:  str
    message: str = "Generation started"


# ---------------------------------------------------------------------------
# /jobs/{job_id}
# ---------------------------------------------------------------------------
class JobResult(BaseModel):
    code:        str
    description: str
    output_file: str
    retries:     int
    run_id:      Optional[str] = None


class JobStatus(BaseModel):
    job_id:   str
    status:   str           # "queued" | "running" | "done" | "failed"
    progress: List[str]     # timestamped log lines
    result:   Optional[JobResult] = None
    error:    Optional[str] = None


# ---------------------------------------------------------------------------
# /history
# ---------------------------------------------------------------------------
class HistoryItem(BaseModel):
    id:          str
    game_idea:   str
    output_file: str
    status:      str
    retries:     int
    description: str
    code_length: int
    created_at:  str


# ---------------------------------------------------------------------------
# /similar
# ---------------------------------------------------------------------------
class SimilarRequest(BaseModel):
    game_idea: str
    k: int = Field(3, ge=1, le=10)


class SimilarResponse(BaseModel):
    results: str    # formatted text ready to display
