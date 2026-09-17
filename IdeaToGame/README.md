# IdeaToGame 🎮

> Turn a plain-English game idea into a playable Pygame game using a 3-agent AI pipeline.

IdeaToGame uses **[CrewAI](https://crewai.com)** and the **[DeepSeek API](https://platform.deepseek.com)** to run three specialised AI agents back-to-back:

| Agent | Role |
|---|---|
| 🎨 Creative Game Designer | Writes a Game Design Document from your idea |
| 💻 Senior Python Developer | Implements the design as a single-file Pygame script |
| 🔍 QA Engineer | Reviews and fixes the code for correctness & playability |

The result is a ready-to-run `*.py` game file — no manual editing needed.

---

## Example Output

| Idea | Generated Game |
|---|---|
| "A fun endless runner where a character jumps over obstacles" | `main.py` — *Dash Runner* |
| "Rotate a spaceship, shoot asteroids that split into smaller pieces" | `spaceship.py` — *Asteroid Splitter* |

---

## Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/your-username/IdeaToGame.git
cd IdeaToGame
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Add your API key
Copy the example env file and fill in your [DeepSeek API key](https://platform.deepseek.com/api_keys):
```bash
cp .env.example .env
# then edit .env and paste your key
```

### 4. Set your game idea
Open `generate_game.py` and change the `GAME_IDEA` constant at the top:
```python
GAME_IDEA   = "Your game idea here"
OUTPUT_FILE = "my_game.py"
```

### 5. Generate & play
```bash
python generate_game.py   # generates the game
python my_game.py         # play it!
```

---

## Project Structure

```
IdeaToGame/
├── generate_game.py   # Main script — runs the AI pipeline
├── requirements.txt   # Python dependencies
├── .env.example       # API key template (copy to .env)
├── .gitignore
├── examples/
│   ├── main.py        # Example: Dash Runner (endless runner)
│   └── spaceship.py   # Example: Asteroid Splitter
└── README.md
```

---

## How It Works

```
Your idea (GAME_IDEA)
        │
        ▼
┌─────────────────────────┐
│  Creative Game Designer │  → Game Design Document (Markdown)
└─────────────────────────┘
        │
        ▼
┌─────────────────────────┐
│  Senior Python Developer│  → Single-file Pygame script
└─────────────────────────┘
        │
        ▼
┌─────────────────────────┐
│  QA Engineer            │  → Reviewed & fixed final code
└─────────────────────────┘
        │
        ▼
    OUTPUT_FILE.py  ← ready to run!
```

---

## Requirements

- Python 3.10+
- A free [DeepSeek API key](https://platform.deepseek.com/api_keys)

---

## Game Idea Suggestions

Paste any of these straight into `GAME_IDEA` to get started:

### 🐦 Flappy Bird Variants
| Idea | `GAME_IDEA` value |
|---|---|
| Classic Flappy | `"A flappy bird clone — tap SPACE to flap wings and fly through gaps between pipes without touching them. Score increases each pipe passed."` |
| Rocket Flappy | `"A flappy bird clone where a rocket ship flies through space dodging asteroid gaps. The gap gets smaller every 10 pipes."` |
| Bouncy Ball | `"Like flappy bird but the player is a bouncing ball that reverses gravity on SPACE. Navigate through gaps in horizontal walls."` |
| Flappy Duo | `"Two-player flappy bird on the same keyboard — player 1 uses SPACE, player 2 uses UP arrow. First to die loses."` |

### 🐍 Snake Variants
| Idea | `GAME_IDEA` value |
|---|---|
| Snake Evolution | `"Classic snake but the arena walls shrink every 30 seconds, adding pressure. Eating food speeds the snake up slightly."` |
| Snake vs Snake | `"Two snakes on the same board controlled by two players on the same keyboard. Crash into each other or the walls to lose."` |
| Portal Snake | `"Snake game where the board has portals — entering one side teleports the snake to the opposite side."` |
| Hungry Snake | `"Snake must eat 3 foods before a timer runs out each round. Each round the snake starts longer and the timer is shorter."` |

### 🕹️ Arcade Classics
| Idea | `GAME_IDEA` value |
|---|---|
| Brick Breaker | `"A brick breaker game with a paddle, bouncing ball, and colorful bricks. Some bricks need multiple hits. Include power-ups like multi-ball and wider paddle."` |
| Pong | `"Two-player pong with paddles on left and right sides. Ball speeds up after each hit. First to 7 points wins."` |
| Frogger | `"Frogger clone where a frog crosses a busy road dodging cars, then crosses a river by hopping on logs. Reach the other side to win."` |
| Pac-Man Lite | `"Top-down maze game where the player collects all dots while avoiding 2 ghosts. Eating a power pellet lets the player eat ghosts temporarily."` |

### ⚔️ Action
| Idea | `GAME_IDEA` value |
|---|---|
| Space Invaders | `"Space invaders where waves of aliens descend toward the player. Player has a shield that degrades when hit. Aliens shoot back randomly."` |
| Vampire Survivors | `"Top-down survivor game where enemies swarm the player from all sides. Player auto-attacks nearest enemy. Collect XP gems to level up and increase damage."` |
| Dungeon Crawler | `"Top-down dungeon crawler where the player fights skeletons with a sword, collects a key, and finds the exit door. 3 lives."` |
| Tower Defense | `"Side-scrolling tower defense — enemies walk along a path, player clicks to place cannons that shoot automatically. Survive 10 waves."` |

### 🧠 Puzzle / Casual
| Idea | `GAME_IDEA` value |
|---|---|
| Tower Stack | `"Stacking game where a platform swings back and forth and the player drops blocks to build the tallest tower without them falling."` |
| Gravity Flipper | `"A game where the player flips gravity with SPACE to navigate a character through a cave without hitting the ceiling or floor."` |
| Color Flood | `"A grid puzzle where the player floods the board from the top-left corner, trying to fill it all in one color in the fewest moves."` |
| Memory Match | `"A card matching game — flip two cards at a time to find pairs. All cards face-down, 4x4 grid. Fewest flips wins."` |

---

## Tips

- **Change the game idea** by editing `GAME_IDEA` in `generate_game.py`
- **Generation takes 2–5 minutes** — the agents are making several LLM calls
- If the generated game has a syntax error, re-run `generate_game.py` (LLM outputs vary slightly)
- All games are self-contained — they only use `pygame`, `sys`, `math`, and `random`
- **Be descriptive** — the more detail in your idea, the better the output

---

## License

MIT — do whatever you want with the generated games.
