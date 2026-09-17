"""
pipeline/nodes/developer.py
---------------------------
Developer node: takes the GDD and writes a complete Pygame implementation.

Returns structured JSON (code, dependencies, description) parsed via Pydantic.
If the LLM returns malformed JSON, falls back to regex extraction.
"""

import json
import re

from langchain_core.output_parsers import StrOutputParser

from pipeline.prompts import DEVELOPER_PROMPT
from pipeline.state import GameState


def _parse_code_response(raw: str) -> dict:
    """
    Parse the LLM response into {code, dependencies, description}.
    Tries JSON first, then falls back to regex extraction of the code block.
    """
    # Strip any accidental markdown fences around the JSON
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)

    # Attempt 1: parse as JSON
    try:
        data = json.loads(cleaned)
        return {
            "game_code":    data.get("code", ""),
            "dependencies": data.get("dependencies", ["pygame", "sys", "random"]),
            "description":  data.get("description", ""),
        }
    except json.JSONDecodeError:
        pass

    # Attempt 2: extract fenced python block
    fenced = re.search(r"```(?:python|py)?\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if fenced:
        return {
            "game_code":    fenced.group(1).strip(),
            "dependencies": ["pygame", "sys", "random"],
            "description":  "",
        }

    # Attempt 3: raw fallback if it looks like Python
    if "import pygame" in raw or "pygame.init()" in raw:
        return {
            "game_code":    raw.strip(),
            "dependencies": ["pygame", "sys", "random"],
            "description":  "",
        }

    raise ValueError("Developer node: could not extract game code from LLM response.")


def developer_node(state: GameState, llm) -> GameState:
    """
    Input state keys:  design_doc, syntax_error (on retry), retries
    Output state keys: game_code, dependencies, description, retries
    """
    retry_num = state.get("retries", 0)
    print(f"\n[Developer] Writing Pygame code (attempt {retry_num + 1})...")

    error_context = (
        "5. DO NOT include any system-specific paths.\n"
        "6. Add the following at the very top of your code to suppress annoying Pygame warnings:\n"
        "   ```python\n"
        "   import warnings\n"
        "   warnings.filterwarnings(\"ignore\", category=UserWarning)\n"
        "   ```\n\n"
    )
    if state.get("syntax_error"):
        error_context += (
            f"IMPORTANT — your previous attempt had this syntax error:\n"
            f"{state['syntax_error']}\n"
            "Fix this specific issue in the new version.\n\n"
        )

    chain = DEVELOPER_PROMPT | llm | StrOutputParser()

    raw = chain.invoke({
        "design_doc":    state["design_doc"],
        "error_context": error_context,
    })

    parsed = _parse_code_response(raw)
    print(f"[Developer] Code written ({len(parsed['game_code'])} chars).")

    return {
        **state,
        "game_code":    parsed["game_code"],
        "dependencies": parsed["dependencies"],
        "description":  parsed["description"],
        "retries":      retry_num + 1,
        "syntax_error": "",   # clear previous error
    }
