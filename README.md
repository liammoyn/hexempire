## Overview

This project is a custom pygame implementation of the old flash game Hex Empire. This game is between 4 players on a hex board that take turns moving armies around the board to capture towns and eventually your opponent's capitals.

To run this project locally:
```
.venv/bin/python main.py
```

To run in a web browser, see the **Web Build** section below.

## Todo
1. Make the options for the game editable through an interface
2. Run evolutionary algorithm to determine the best values for the CPU players
3. Tasks in the `plan.txt` file

## Environment

Set up a Python virtual environment and install dependencies (tested on macOS with `zsh`):

```
# create venv and install
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# alternatively run the helper script
bash scripts/setup_env.sh
```

Notes:
- This project requires `pygame-ce`, `numpy`, and `pygbag` (listed in `requirements.txt`).
- The `scripts/setup_env.sh` script will create or reuse `.venv`, upgrade `pip`, and install from `requirements.txt`.

## Web Build

The game can be run in a browser via [pygbag](https://pygame-web.github.io/), which compiles the pygame loop to WebAssembly.

**First-time setup** (once per machine, after the venv is created):

```bash
# Generate the HTML shell from template.tmpl — wait for "Serving python files from..." then Ctrl+C
.venv/bin/python -m pygbag --port 8000 --template template.tmpl main.py

# Build the game bundle and download the pygame-ce WASM wheel
.venv/bin/python build_web.py
```

**After any code change:**

```bash
.venv/bin/python build_web.py
.venv/bin/python -m http.server 8000 --directory build/web
```

Then open **http://localhost:8000** in a browser. Click the page to dismiss the start prompt; on first load the WASM runtime (~25 MB) downloads from the pygbag CDN and is cached for subsequent runs.

**Controls:**
- `Space` — new game
- `S` — toggle stepping mode (pauses before each AI move; press `Right Arrow` to step, `Left Arrow` to undo)
- `E` — end turn (when playing as a human player)
- `P` / `L` — save / load a game state
