## Overview

This project is a custom pygame implementation of the old flash game Hex Empire. This game is between 4 players on a hex board that take turns moving armies around the board to capture towns and eventually your opponent's capitals.

To run this project, you first need to edit the font that pygame uses in the `main.py` file. Then run:
```
python main.py
```

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
- This project requires `pygame` and `numpy` (listed in `requirements.txt`).
- The `scripts/setup_env.sh` script will create or reuse `.venv`, upgrade `pip`, and install from `requirements.txt`.
