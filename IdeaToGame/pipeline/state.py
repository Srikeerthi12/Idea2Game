"""
pipeline/state.py
-----------------
Defines the shared state that flows through every node in the LangGraph pipeline.
Each node reads from and writes back to this state object.
"""

from typing import TypedDict


class GameState(TypedDict):
    # ── Inputs ────────────────────────────────────────────────────
    game_idea: str          # plain-English idea from the user
    output_file: str        # filename to save the generated game to

    # ── Pipeline outputs (filled by each node) ────────────────────
    similar_games: str      # RAG context: past similar game designs
    design_doc: str         # Game Design Document from Designer node
    game_code: str          # raw Python code from Developer node
    dependencies: list      # e.g. ["pygame", "sys", "random"]
    description: str        # one-line summary of the generated game

    # ── Retry / error tracking ────────────────────────────────────────────
    retries: int            # how many times Developer has been retried
    max_retries: int        # maximum allowed retries (default 3)
    syntax_error: str       # last syntax error message (if any)
    status: str             # "success" | "failed" | "retrying"

    # ── Persistence (filled by save_node) ────────────────────────────────
    run_id: str             # UUID from Supabase — used to cross-ref ChromaDB
