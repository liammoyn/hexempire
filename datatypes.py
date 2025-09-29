import dataclasses as dcs
import uuid
from enum import Enum

BC = 0
BR = 1
TR = 2
TC = 3
TL = 4
BL = 5
PlayerColors = ["red", "purple", "cyan", (0, 255, 0)]
PlayerNames = ["Red", "Purple", "Blue", "Green"]

class GameProgress(Enum):
	WAITING=0
	RUNNING=1
	OVER=2

@dcs.dataclass(frozen=True)
class Coord:
	col: int
	row: int

@dcs.dataclass(frozen=True)
class Space:
	coord: Coord
	isWater: bool
	isCapital: bool = False
	ownedBy: int = -1
	firstOwner: int = -1
	isCoastal: bool = False
	isInland: bool = False
	isPort: bool = False
	isTown: bool = False
	borderColors: list[str] = dcs.field(default_factory=lambda: [None, None, None, None, None, None])
	borderIsWater: list[str] = dcs.field(default_factory=lambda: [False, False, False, False, False, False])
	pointToMoves: dict[Coord, int] = dcs.field(default_factory=lambda: {})
	sortedPoints: list[Coord] = dcs.field(default_factory=lambda: [])

@dcs.dataclass(frozen=True)
class Army:
	aid: uuid.uuid4
	coord: Coord
	ownedBy: int = -1
	strength: int = 1
	morale: int = 0
	canMove: bool = True

@dcs.dataclass(frozen=True)
class Board:
	grid: list[Space]
	cols: int
	rows: int
	armies: dict[Coord, Army]
	seed: int

@dcs.dataclass(frozen=True)
class Geometry:
	width: float
	height: float
	points: list[(float, float)]
	angles: list[float]
	runningAngles: list[float]

@dcs.dataclass(frozen=True)
class Move:
	fromCoord: Coord
	toCoord: Coord
	isEndTurn: bool = False

@dcs.dataclass(frozen=True)
class GameStatus:
	board: Board
	gameProgress: GameProgress
	moveCounter: int
	currentTurn: int = -1
	movesLeft: int = 0