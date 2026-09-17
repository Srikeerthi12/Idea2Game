"""
generate_game.py
================
Entry point for IdeaToGame v2.

Uses a LangGraph pipeline (Designer → Developer → QA) powered by DeepSeek.
Automatically retries up to 3 times if the generated code has syntax errors.

Usage:
    1. Copy .env.example to .env and fill in your keys
    2. pip install -r requirements.txt
    3. Edit GAME_IDEA and OUTPUT_FILE below
    4. python generate_game.py
"""

import os
import sys
from pathlib import Path

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# Configuration — edit these to generate a different game
# ---------------------------------------------------------------------------
GAME_IDEA   = "Asteroid blaster but cannons in the front like this |__|"
OUTPUT_FILE = "spaceship3.py"

# ---------------------------------------------------------------------------
# Load .env (supports KEY=value and KEY:value formats)
# ---------------------------------------------------------------------------
def load_dotenv(path: Path) -> None:
    if not path.exists():
        print("[WARN] No .env file found.")
        return
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
            elif ":" in line:
                k, v = line.split(":", 1)
            else:
                continue
            os.environ.setdefault(k.strip(), v.strip())
    print("[OK] .env loaded.")


load_dotenv(Path(__file__).parent / ".env")

# ---------------------------------------------------------------------------
# Run the pipeline
# ---------------------------------------------------------------------------
from pipeline.graph import run_pipeline

final_state = run_pipeline(game_idea=GAME_IDEA, output_file=OUTPUT_FILE)

# ---------------------------------------------------------------------------
# Report result
# ---------------------------------------------------------------------------
print("\n" + "-" * 60)

if final_state["status"] == "success":
    print(f"[DONE] Game generated successfully!")
    print(f"       File    : {OUTPUT_FILE}")
    print(f"       Summary : {final_state.get('description', 'N/A')}")
    print(f"       Retries : {final_state.get('retries', 0) - 1}")
    print(f"\nRun:  python {OUTPUT_FILE}")

elif final_state["status"] == "failed":
    print(f"[FAIL] Generation failed after {final_state.get('retries', 0)} retries.")
    print(f"       Last error: {final_state.get('syntax_error', 'unknown')}")
    print(f"       The partial code was still saved to {OUTPUT_FILE} — inspect it manually.")

print("-" * 60)
