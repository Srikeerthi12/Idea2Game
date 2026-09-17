"""
pipeline/prompts.py
-------------------
All prompt templates for the three LangGraph nodes.
Keeping prompts in one place makes them easy to tune without touching node logic.
"""

from langchain_core.prompts import ChatPromptTemplate


# ---------------------------------------------------------------------------
# Game Designer prompt
# ---------------------------------------------------------------------------
DESIGNER_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an experienced game designer who turns ideas into clear, "
        "concise Game Design Documents (GDDs). "
        "Keep the scope small enough for a single-file Pygame implementation. "
        "Be specific about: objective, controls, entities, win/lose conditions, "
        "core mechanics, scoring, and gameplay loop."
    ),
    (
        "human",
        "Game idea: {game_idea}\n\n"
        "{similar_games_context}"
        "Write a clear, detailed Markdown Game Design Document for this game."
    ),
])

# ---------------------------------------------------------------------------
# Developer prompt
# ---------------------------------------------------------------------------
DEVELOPER_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a senior Python engineer specialised in Pygame. "
        "You write clean, complete, runnable code with a proper game loop, "
        "event handling, drawing, collision detection, scoring, and quit handling. "
        "You always produce a self-contained single-file Python game.\n\n"
        "IMPORTANT: Return ONLY a raw JSON object — no markdown, no explanation.\n"
        "Format:\n"
        '{{"code": "<full python source>", '
        '"dependencies": ["pygame", "sys"], '
        '"description": "<one line summary>"}}'
    ),
    (
        "human",
        "Game Design Document:\n\n{design_doc}\n\n"
        "{error_context}"
        "Write the complete Python Pygame implementation. "
        "Return only the JSON object described above."
    ),
])

# ---------------------------------------------------------------------------
# QA / Reviewer prompt
# ---------------------------------------------------------------------------
QA_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a meticulous QA engineer and Python code reviewer. "
        "Review Pygame code for: syntax errors, missing imports, broken game loop, "
        "collision logic, scoring, quit handling, and any obvious runtime bugs. "
        "Fix all issues and return the corrected code.\n\n"
        "IMPORTANT: Return ONLY a raw JSON object — no markdown, no explanation.\n"
        "Format:\n"
        '{{"code": "<corrected full python source>", '
        '"dependencies": ["pygame", "sys"], '
        '"description": "<one line summary>"}}'
    ),
    (
        "human",
        "Game Design Document:\n\n{design_doc}\n\n"
        "Code to review:\n\n{game_code}\n\n"
        "Review, fix all issues, and return the corrected JSON object."
    ),
])
