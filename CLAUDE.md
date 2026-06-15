## Overview

A pygame-ce reimplementation of the flash game Hex Empire — 4-player turn-based strategy on a hex grid. Players move armies to capture towns, ports, and capitals. The game runs locally and in a browser via pygbag/WASM.

## Commands

```bash
# Run locally
.venv/bin/python main.py

# Web build (after first-time setup)
.venv/bin/python build_web.py
.venv/bin/python -m http.server 8000 --directory build/web

# First-time web setup (run once, Ctrl+C when "Serving python files..." appears)
.venv/bin/python -m pygbag --port 8000 --template template.tmpl main.py

# Environment setup
bash scripts/setup_env.sh
```

There are no tests or linting commands.

## Architecture

**Data model** (`datatypes.py`): All core types are frozen dataclasses — `Board`, `Space`, `Army`, `Coord`, `Move`, `GameStatus`. All state mutations return new objects; nothing is mutated in place.

**Board logic** (`board.py`): Pure functions that take and return `Board`. Covers board generation (water seeding, ports, towns, capitals), army movement/combat (`moveArmy`, `determineFightOutcome`, `determineMergeOutcome`), turn management (`endTurn`, `addTurnStrength`, `addTurnMorale`), and the hex movement graph (`get2NeighborSpaces`, `getMovesForArmy`). The board stores a precomputed `pointToMoves` graph on each `Space` for AI pathfinding.

**Hex geometry** (`hexutils.py`): Offset-coordinate hex math (odd-column offset layout). Direction constants `TL/TC/TR/BL/BC/BR` are defined in `datatypes.py`.

**Game loop** (`main.py → MainRender`): Owns the pygame display and the `asyncio` loop required by pygbag. Drives AI moves synchronously inline (no threads) — pygbag compatibility requires `await asyncio.sleep(0)` each frame. AI moves are computed in the main loop body and passed to `GameStateController`.

**Game state** (`gamecontroller.py → GameStateController`): Mediates between board logic and rendering. Tracks whose turn it is, moves remaining, stepping mode, and serialisation (`getGameStateString` / `useGameStateString`). Handles both user clicks and computer move submissions.

**Rendering** (`renders/`):
- `boardrender.py (GBoard)` — draws hex grid, armies, highlights, battle-scar animations, eval overlays
- `backgroundrender.py` — terrain/water tiles
- `armyrender.py` — army strength/morale bubbles
- `spacerender.py` — space-level rendering (ports, towns, capitals)
- `evalrender.py` — AI evaluation overlay
- `inputrender.py / statusrender.py` — HUD widgets

**AI players** (`players/`):
- `EvaluationPlayer` — greedy single-move lookahead; scores moves by weighted sum of army strength, morale, and strength-generation changes
- `ObjectivePlayer` — extends evaluation with objective-based pathfinding (uses `Space.sortedPoints` / `pointToMoves`)
- `NaivePlayer` — random valid moves
- `ComputerWrapper` — thin adapter; all players expose `requestMove(board, movesLeft) -> (Move, moveEvals, objectiveEvals)`

**Web build** (`build_web.py`): Bundles source into `build/web/hexempire.apk` (zip) and `.tar.gz`. The pygbag runtime fetches the pygame-ce WASM wheel from CDN on first browser load (~25 MB, cached).

## Key constraints

- **pygbag compatibility**: the main loop must use `async def` and `await asyncio.sleep(0)` each frame. No background threads.
- **Immutable board**: always use `dataclasses.replace(...)` and `updateBoard(...)` — never mutate `Space`, `Army`, or `Board` fields directly.
- **Hex coordinate system**: odd-column offset. Neighbor lookups use `getFixedNeighborCoords` (returns all 6 regardless of board bounds) vs `getNeighborCoords` (filters to valid coords).
- **isComputerCheck flag**: pass `isComputerCheck=True` to `moveArmy` / `updateOwned` when the AI is simulating moves — skips the expensive `addBorders` graphical update.
