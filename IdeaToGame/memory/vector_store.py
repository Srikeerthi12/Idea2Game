"""
memory/vector_store.py
----------------------
ChromaDB helpers for storing and retrieving past generated games.

Every successful game generation is embedded and stored here.
Before the Designer agent runs, it searches this store for similar
past games to avoid repetition and build on proven designs.

Embeddings use ChromaDB's built-in default function (all-MiniLM-L6-v2)
which runs locally — no extra API key needed.
"""

import os
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from typing import Optional

# ---------------------------------------------------------------------------
# ChromaDB client (persists to local disk)
# ---------------------------------------------------------------------------
_CHROMA_DIR = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db")

_client: Optional[chromadb.PersistentClient] = None
_collection = None


def _get_collection():
    """Lazily initialise the ChromaDB client and collection."""
    global _client, _collection
    if _collection is None:
        Path(_CHROMA_DIR).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=_CHROMA_DIR)
        ef = embedding_functions.DefaultEmbeddingFunction()  # all-MiniLM-L6-v2
        _collection = _client.get_or_create_collection(
            name="games",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def store_game(
    run_id: str,
    game_idea: str,
    design_doc: str,
    game_code: str,
    output_file: str,
    description: str = "",
) -> None:
    """
    Embed and store a successfully generated game.

    The document stored is the Game Design Document (GDD) — this is what
    the Designer agent searches against, so similar future designs can be
    retrieved as context.

    Args:
        run_id:      Unique ID for this run (use Supabase row id or UUID).
        game_idea:   The original plain-English idea.
        design_doc:  The full GDD text (what gets embedded).
        game_code:   The generated Python source (stored as metadata).
        output_file: Filename the code was saved to.
        description: One-line summary from the QA agent.
    """
    try:
        col = _get_collection()
        col.upsert(
            ids=[run_id],
            documents=[design_doc],        # embedded for similarity search
            metadatas=[{
                "game_idea":   game_idea,
                "output_file": output_file,
                "description": description,
                # Store first 500 chars of code as preview (ChromaDB metadata limit)
                "code_preview": game_code[:500],
            }],
        )
        print(f"[ChromaDB] Stored game '{output_file}' (id={run_id}).")
    except Exception as exc:
        print(f"[ChromaDB] WARNING: Could not store game — {exc}")


def search_similar(game_idea: str, k: int = 3) -> str:
    """
    Semantic search for games similar to the given idea.

    Returns a formatted string ready to inject into the Designer prompt,
    or an empty string if the store is empty or search fails.

    Args:
        game_idea: The new game idea to find similar designs for.
        k:         Number of similar games to retrieve.
    """
    try:
        col = _get_collection()
        if col.count() == 0:
            return ""

        results = col.query(
            query_texts=[game_idea],
            n_results=min(k, col.count()),
            include=["documents", "metadatas", "distances"],
        )

        if not results["documents"] or not results["documents"][0]:
            return ""

        lines = []
        # Zip documents, metadata, and distance
        for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
            # Cosine distance: 0 is identical, > 0.6 is likely irrelevant for all-MiniLM
            if dist > 0.6:
                continue
                
            lines.append(
                f"- **{meta.get('output_file', 'unknown')}**: "
                f"{meta.get('description', 'no description')}\n"
                f"  Idea: {meta.get('game_idea', '')}\n"
                f"  GDD excerpt: {doc[:300]}...\n"
            )

        if not lines:
            print("[ChromaDB] No sufficiently similar games found (all below threshold).")
            return ""

        print(f"[ChromaDB] Found {len(lines)} similar game(s).")
        return "\n".join(lines)

    except Exception as exc:
        print(f"[ChromaDB] WARNING: Search failed — {exc}")
        return ""
