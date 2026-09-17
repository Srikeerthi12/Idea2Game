"""
pipeline/graph.py
-----------------
Builds and compiles the LangGraph pipeline.

Graph flow (Phase 2):
    START
      │
      ▼
  [designer]   — RAG search ChromaDB → writes GDD
      │
      ▼
  [developer]  — writes Pygame code
      │
      ▼
    [qa]        — reviews + ast.parse syntax check
      │
      ├── "success"  ──▶ [save] ──▶ END
      ├── "retrying" ──▶ [developer]  (retry loop, max 3)
      └── "failed"   ──▶ [save] ──▶ END

  [save] — stores to ChromaDB (if success) + logs to Supabase (always)
"""

import os
from functools import partial
from pathlib import Path

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from memory.db import log_run
from memory.vector_store import store_game
from pipeline.nodes.designer import designer_node
from pipeline.nodes.developer import developer_node
from pipeline.nodes.qa import qa_node
from pipeline.state import GameState


# ---------------------------------------------------------------------------
# Build shared LLM (DeepSeek via OpenAI-compatible client)
# ---------------------------------------------------------------------------
def _build_llm() -> ChatOpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY not set. Check your .env file.")

    return ChatOpenAI(
        model="deepseek-chat",
        api_key=api_key,
        base_url="https://api.deepseek.com",
        temperature=0.2,
        max_tokens=6000,
    )


# ---------------------------------------------------------------------------
# Save node — runs after QA regardless of success/failure
# ---------------------------------------------------------------------------
def save_node(state: GameState) -> GameState:
    """
    Handles all persistence after the pipeline completes:
      1. Saves game code to disk
      2. Logs the run to Supabase (always)
      3. Stores GDD + code in ChromaDB (only on success)
      1. Logs the run to Supabase (always)
      2. Stores GDD + code in ChromaDB (only on success)
    """
    output_file = state.get("output_file", "game.py")
    game_code   = state.get("game_code", "")
    status      = state.get("status", "failed")

    # Write to Supabase (Database)
    run_id = log_run(
        game_idea   = state.get("game_idea", ""),
        output_file = output_file,
        status      = status,
        retries     = state.get("retries", 0),
        description = state.get("description", ""),
        code_length = len(game_code),
        game_code   = game_code,
    )

    # 3. Store in ChromaDB (only on success — don't pollute the store with broken code)
    if status == "success" and game_code and state.get("design_doc"):
        store_game(
            run_id      = run_id,
            game_idea   = state.get("game_idea", ""),
            design_doc  = state.get("design_doc", ""),
            game_code   = game_code,
            output_file = output_file,
            description = state.get("description", ""),
        )

    return {**state, "run_id": run_id}


# ---------------------------------------------------------------------------
# Routing function — decides next node after QA
# ---------------------------------------------------------------------------
def _route_after_qa(state: GameState) -> str:
    if state["status"] == "retrying":
        return "developer"
    # "success" or "failed" both go to save
    return "save"


# ---------------------------------------------------------------------------
# Build and compile the graph
# ---------------------------------------------------------------------------
def build_graph():
    llm = _build_llm()

    # Bind LLM into agent nodes via partial so nodes stay pure functions
    _designer  = partial(designer_node,  llm=llm)
    _developer = partial(developer_node, llm=llm)
    _qa        = partial(qa_node,        llm=llm)

    graph = StateGraph(GameState)

    graph.add_node("designer",  _designer)
    graph.add_node("developer", _developer)
    graph.add_node("qa",        _qa)
    graph.add_node("save",      save_node)   # Phase 2: persistence node

    graph.add_edge(START,       "designer")
    graph.add_edge("designer",  "developer")
    graph.add_edge("developer", "qa")
    graph.add_edge("save",      END)

    # QA conditional: retry → developer, done → save
    graph.add_conditional_edges("qa", _route_after_qa, {
        "developer": "developer",
        "save":      "save",
    })

    return graph.compile()


# ---------------------------------------------------------------------------
# Run the pipeline end-to-end
# ---------------------------------------------------------------------------
def run_pipeline(game_idea: str, output_file: str = "game.py") -> GameState:
    """
    Runs the full Designer → Developer → QA → Save pipeline.
    Returns the final GameState.
    """
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
    }

    print(f"\n[Pipeline] Starting: '{game_idea}'")
    final_state = graph.invoke(initial_state)
    return final_state
