"""
pipeline/nodes/qa.py
--------------------
QA node: reviews the developer's code, fixes issues, then runs a
Python syntax check.

If the syntax check passes  → status = "success"
If the syntax check fails   → status = "retrying" (LangGraph will loop back)
If max retries exhausted    → status = "failed"
"""

import ast
import json
import re

from langchain_core.output_parsers import StrOutputParser

from pipeline.prompts import QA_PROMPT
from pipeline.state import GameState


def _parse_code_response(raw: str) -> dict:
    """Same robust parser as developer node."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)

    try:
        data = json.loads(cleaned)
        return {
            "game_code":    data.get("code", ""),
            "dependencies": data.get("dependencies", ["pygame", "sys", "random"]),
            "description":  data.get("description", ""),
        }
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:python|py)?\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if fenced:
        return {
            "game_code":    fenced.group(1).strip(),
            "dependencies": ["pygame", "sys", "random"],
            "description":  "",
        }

    if "import pygame" in raw or "pygame.init()" in raw:
        return {
            "game_code":    raw.strip(),
            "dependencies": ["pygame", "sys", "random"],
            "description":  "",
        }

    raise ValueError("QA node: could not extract game code from LLM response.")


def _check_syntax(code: str) -> str | None:
    """
    Returns None if syntax is valid, or an error message string if not.
    Uses ast.parse which is faster than py_compile and doesn't write .pyc files.
    """
    try:
        ast.parse(code)
        return None
    except SyntaxError as e:
        return f"SyntaxError at line {e.lineno}: {e.msg}"


def qa_node(state: GameState, llm) -> GameState:
    """
    Input state keys:  design_doc, game_code, retries, max_retries
    Output state keys: game_code, dependencies, description, syntax_error, status
    """
    print("\n[QA] Reviewing and fixing code...")

    chain = QA_PROMPT | llm | StrOutputParser()

    raw = chain.invoke({
        "design_doc": state["design_doc"],
        "game_code":  state["game_code"],
    })

    parsed    = _parse_code_response(raw)
    new_code  = parsed["game_code"]
    print(f"[QA] Review complete ({len(new_code)} chars). Running syntax check...")

    # Syntax check
    error = _check_syntax(new_code)

    if error is None:
        print("[QA] Syntax OK — pipeline complete.")
        return {
            **state,
            "game_code":    new_code,
            "dependencies": parsed["dependencies"],
            "description":  parsed["description"],
            "syntax_error": "",
            "status":       "success",
        }

    # Syntax failed
    retries     = state.get("retries", 0)
    max_retries = state.get("max_retries", 3)

    print(f"[QA] Syntax error: {error}  (retry {retries}/{max_retries})")

    if retries >= max_retries:
        print("[QA] Max retries reached — marking as failed.")
        return {
            **state,
            "game_code":    new_code,
            "syntax_error": error,
            "status":       "failed",
        }

    return {
        **state,
        "game_code":    new_code,
        "syntax_error": error,
        "status":       "retrying",
    }
