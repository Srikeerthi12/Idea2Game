"""
api/routes/generate.py
----------------------
POST /generate  — starts a background game generation job
GET  /jobs/{job_id} — polls job status + real-time progress log

Uses a thread pool to run the synchronous LangGraph pipeline
without blocking the FastAPI event loop.
LangChain callbacks capture per-agent progress into the job log.
"""

import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from fastapi import APIRouter, HTTPException
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from api.models import GenerateRequest, GenerateResponse, JobResult, JobStatus

router = APIRouter()

# ---------------------------------------------------------------------------
# In-memory job store  {job_id: {status, progress, result, error}}
# ---------------------------------------------------------------------------
jobs: Dict[str, dict] = {}

# Thread pool for running the synchronous pipeline
_executor = ThreadPoolExecutor(max_workers=3)

# Agent names in call order (Designer → Developer → QA)
_AGENT_NAMES = ["🎨 Designer", "💻 Developer", "🔍 QA"]


# ---------------------------------------------------------------------------
# LangChain progress callback — fires on every LLM call
# ---------------------------------------------------------------------------
class _ProgressCallback(BaseCallbackHandler):
    """Appends timestamped messages to the job's progress list."""

    def __init__(self, progress_list: list):
        super().__init__()
        self._progress = progress_list
        self._call_index = 0  # counts LLM calls: 0=Designer, 1=Developer, 2=QA

    def _log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self._progress.append(f"[{ts}] {msg}")

    def on_llm_start(self, serialized, prompts, **kwargs):
        name = _AGENT_NAMES[self._call_index] if self._call_index < 3 else "Agent"
        self._log(f"{name}: Calling DeepSeek API...")

    def on_llm_end(self, response: LLMResult, **kwargs):
        name = _AGENT_NAMES[self._call_index] if self._call_index < 3 else "Agent"
        self._log(f"{name}: Response received ✓")
        self._call_index += 1

    def on_llm_error(self, error, **kwargs):
        self._log(f"⚠ LLM error: {str(error)[:120]}")


# ---------------------------------------------------------------------------
# Background task — runs the full pipeline in a thread
# ---------------------------------------------------------------------------
def _pipeline_task(job_id: str, game_idea: str, output_file: str):
    """Synchronous pipeline runner. Executed inside the thread pool."""
    progress = jobs[job_id]["progress"]

    def log(msg: str):
        ts = time.strftime("%H:%M:%S")
        progress.append(f"[{ts}] {msg}")

    jobs[job_id]["status"] = "running"
    log("🚀 Pipeline starting...")

    try:
        # Import here to avoid circular imports at module load time
        from pipeline.graph import build_graph
        from pipeline.state import GameState

        callback = _ProgressCallback(progress)

        graph = build_graph()

        initial_state: GameState = {
            "game_idea":     game_idea,
            "output_file":   output_file,
            "similar_games": "",
            "design_doc":    "",
            "game_code":     "",
            "dependencies":  [],
            "description":   "",
            "retries":       0,
            "max_retries":   3,
            "syntax_error":  "",
            "status":        "",
            "run_id":        "",
        }

        log(f"🔍 Searching ChromaDB for similar past games...")
        final_state = graph.invoke(
            initial_state,
            config={"callbacks": [callback]},
        )

        status = final_state.get("status", "failed")

        if status == "success":
            jobs[job_id]["status"] = "done"
            jobs[job_id]["result"] = {
                "code":        final_state.get("game_code", ""),
                "description": final_state.get("description", ""),
                "output_file": output_file,
                "retries":     max(0, final_state.get("retries", 1) - 1),
                "run_id":      final_state.get("run_id", ""),
            }
            log(f"✅ Game generated: {output_file}")
        else:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = final_state.get("syntax_error", "Unknown error")
            log(f"❌ Generation failed: {jobs[job_id]['error']}")

    except Exception as exc:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(exc)
        ts = time.strftime("%H:%M:%S")
        progress.append(f"[{ts}] ❌ Exception: {str(exc)[:200]}")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post("/generate", response_model=GenerateResponse, status_code=202)
async def start_generation(request: GenerateRequest):
    """Start a game generation job. Returns a job_id to poll for status."""
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status":   "queued",
        "progress": [],
        "result":   None,
        "error":    None,
    }
    # Run pipeline in thread pool (non-blocking)
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        _executor,
        _pipeline_task,
        job_id,
        request.game_idea,
        request.output_file,
    )
    return GenerateResponse(job_id=job_id)


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Poll this endpoint every 2 seconds to get live progress updates."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    result = None
    if job.get("result"):
        result = JobResult(**job["result"])

    return JobStatus(
        job_id   = job_id,
        status   = job["status"],
        progress = job["progress"],
        result   = result,
        error    = job.get("error"),
    )
