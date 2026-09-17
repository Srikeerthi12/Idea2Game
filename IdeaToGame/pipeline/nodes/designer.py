"""
pipeline/nodes/designer.py
--------------------------
Game Designer node: takes the user's game idea and produces a
detailed Game Design Document (GDD).

Phase 2: Before generating, searches ChromaDB for similar past games
and injects them as context — so the Designer avoids repeating mechanics
already seen and can build on proven designs.
"""

from langchain_core.output_parsers import StrOutputParser

from memory.vector_store import search_similar
from pipeline.prompts import DESIGNER_PROMPT
from pipeline.state import GameState


def designer_node(state: GameState, llm) -> GameState:
    """
    Input state keys:  game_idea, similar_games (pre-filled by retrieve step or empty)
    Output state keys: design_doc, similar_games (updated if search runs here)
    """
    print("\n[Designer] Searching ChromaDB for similar past games...")
    similar_games = search_similar(state["game_idea"], k=3)

    if similar_games:
        print("[Designer] Context found — injecting into prompt.")
    else:
        print("[Designer] No similar games yet — designing from scratch.")

    print("[Designer] Generating Game Design Document...")

    similar_games_context = ""
    if similar_games:
        similar_games_context = (
            "For reference, here are similar games previously generated "
            "(avoid repeating the same mechanics — build on or differentiate from these):\n\n"
            f"{similar_games}\n\n"
        )

    chain = DESIGNER_PROMPT | llm | StrOutputParser()

    design_doc = chain.invoke({
        "game_idea":              state["game_idea"],
        "similar_games_context":  similar_games_context,
    })

    print(f"[Designer] GDD complete ({len(design_doc)} chars).")

    return {**state, "design_doc": design_doc, "similar_games": similar_games}
