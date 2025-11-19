import pygame as pg
import board as b
from renders.spacerender import GSpace
from renders.armyrender import GArmy
from renders.evalrender import GEval
from renders.backgroundrender import GBackground
from datatypes import Coord

class GBoard():
	def __init__(self, GAME_FONT, clock, board, hexW, hexH):
		self.GAME_FONT = GAME_FONT
		self.clock = clock
		self.hexW = hexW
		self.hexH = hexH
		self.board = board
		self.background = GBackground(clock, board, hexW, hexH)
		self.dyingGarmies = []
		self.garmies = {} # Coord to GArmy
		self.gspaces = {} # Coord to GSpace
		self.gevals = {} # Coord to GEval
		self.refreshBoard(board)

	def draw(self, screen, mousePos):
		largeMouseRect = None
		smallMouseRect = None
		if mousePos is not None:
			largeHoverSize = self.hexW * 3
			smallHoverSize = self.hexW
			largeMouseRect = pg.Rect(mousePos - pg.Vector2(largeHoverSize / 2, largeHoverSize / 2), (largeHoverSize, largeHoverSize))
			smallMouseRect = pg.Rect(mousePos - pg.Vector2(smallHoverSize / 2, smallHoverSize / 2), (smallHoverSize, smallHoverSize))

		self.background.draw(screen)

		for gspace in self.gspaces.values():
			gspace.draw(screen, gspace.collidePoint(mousePos))

		gevalsToDraw = []
		for geval in self.gevals.values():
			shouldDraw = smallMouseRect is not None and smallMouseRect.collidepoint(geval.center)
			if shouldDraw:
				gevalsToDraw.append(geval)

		for garmy in self.garmies.values():
			showNumber = largeMouseRect is not None and largeMouseRect.collidepoint(garmy.center) and len(gevalsToDraw) == 0
			garmy.draw(screen, showNumber)

		for geval in gevalsToDraw:
			geval.draw(screen)

		# TODO: Maybe slower than necessary
		newDyingGarmies = [ ga for ga in self.dyingGarmies if not ga.isFinished ]
		for dyingGarmy in newDyingGarmies:
			dyingGarmy.draw(screen, False)
		self.dyingGarmies = newDyingGarmies

	def _parseEvalDicts(self, moveEvals, objectiveEvals) -> (dict[Coord, list[Coord, float, float]], (float, float), (float, float)):
		"""
		moveEvals: dict[Move, float]
		objectiveEvals: dict[Move, float]
		Return1: Dict from an army coord to a list of coords with their moveEval and objectiveEval
		Return2: Tuple of worst moveEval and best moveEval
		Return3: Tuple of worst objectiveEval and best objectiveEval
		"""
		moveEvRange = None
		objectiveEvRange = None
		newCoordToCoordEvals = {}
		allMoves = moveEvals.keys() | objectiveEvals.keys()
		for move in allMoves:
			moveEval = moveEvals.get(move, None)
			objectiveEval = objectiveEvals.get(move, None)
			oldList = newCoordToCoordEvals.get(move.fromCoord, [])
			newList = oldList + [ (move.toCoord, moveEval, objectiveEval) ]
			newCoordToCoordEvals[move.fromCoord] = newList
			if moveEval is not None:
				if moveEvRange is None:
					moveEvRange = (moveEval, moveEval)
				else:
					moveEvRange = (min(moveEvRange[0], moveEval), max(moveEvRange[1], moveEval))
			if objectiveEval is not None:
				if objectiveEvRange is None:
					objectiveEvRange = (objectiveEval, objectiveEval)
				else:
					objectiveEvRange = (min(objectiveEvRange[0], objectiveEval), max(objectiveEvRange[1], objectiveEval))
		return (newCoordToCoordEvals, moveEvRange, objectiveEvRange)


	def handleComputerEvals(self, moveEvals, objectiveEvals):
		coordToCoordEvals, moveEvRange, objectiveEvRange = self._parseEvalDicts(moveEvals, objectiveEvals)
		newGEvals = {}
		for armyCoord, coordWithEvals in coordToCoordEvals.items():
			geval = GEval(
				self.GAME_FONT,
				self.hexW,
				self.hexH,
				armyCoord,
				coordWithEvals,
				moveEvRange,
				objectiveEvRange
			)
			newGEvals[armyCoord] = geval
		self.gevals = newGEvals


	def getSpaceAt(self, pos):
		space = None
		for gspace in self.gspaces.values():
			if gspace.collidePoint(pos):
				space = gspace.space
		return space

	def getArmyAt(self, pos):
		space = self.getSpaceAt(pos)
		if space is not None and space.coord in self.garmies:
			return self.garmies[space.coord].army
		else:
			return None

	def highlightSpace(self, space, isHighlight):
		gspace = self.gspaces.get(space.coord, None)
		if gspace is not None:
			gspace.changeHighlight(isHighlight)

	def highlightCoord(self, coord, isHighlight):
		gspace = self.gspaces.get(coord, None)
		if gspace is not None:
			gspace.changeHighlight(isHighlight)

	def highlightArmy(self, army, isHighlight):
		gspace = self.gspaces.get(army.coord, None)
		if gspace is not None:
			gspace.changeHighlight(isHighlight)

	def unhighlightAll(self):
		for gspace in self.gspaces.values():
			gspace.changeHighlight(False)

	def refreshBoard(self, newBoard):
		self.gevals = {}
		self.refreshGSpaces(newBoard)
		self.refreshGArmies(newBoard)
		self.board = newBoard

	def refreshBoardMove(self, newBoard, movedToCoord):
		self.gevals = {}
		self.refreshGSpaces(newBoard)
		self.refreshGArmies(newBoard, movedToCoord)
		self.board = newBoard

	def refreshGSpaces(self, newBoard) -> list[GSpace]:
		coordToNewSpace = {}
		for space in b.getAllSpaces(newBoard):
			coordToNewSpace[space.coord] = space
		if len(self.gspaces) == 0:
			for c, s in coordToNewSpace.items():
				newGSpace = GSpace(self.clock, self.GAME_FONT, s, c.col, c.row, self.hexW, self.hexH)
				self.gspaces[c] = newGSpace
		else:
			for c, gs in self.gspaces.items():
				newSpace = coordToNewSpace[c]
				gs.refreshSpace(newSpace)


	def refreshGArmies(self, newBoard, movedToCoord = None) -> { Coord: GArmy }:
		idToOldGArmy = { ga.army.aid: ga for ga in self.garmies.values() }
		idToNewArmy = { army.aid: army for army in newBoard.armies.values() }
		getNewGArmy = lambda a: GArmy(self.GAME_FONT, self.clock, a, a.coord.col, a.coord.row, self.hexW, self.hexH)

		newDyingGarmies = [ ga for aid, ga in idToOldGArmy.items() if aid not in idToNewArmy ]
		for garmy in newDyingGarmies:
			deathCoord = garmy.army.coord if movedToCoord is None else movedToCoord
			isBomb = newBoard.armies.get(deathCoord, garmy).ownedBy != garmy.army.ownedBy
			if isBomb:
				self.background.addExplosion(movedToCoord)
			garmy.beginDeath(deathCoord, isBomb)
			self.dyingGarmies.append(garmy)

		newGArmies = {}
		for c, newArmy in newBoard.armies.items():
			gArmy = idToOldGArmy.get(newArmy.aid, getNewGArmy(newArmy))
			gArmy.refreshArmy(newArmy, b.getSpaceFromCoord(newBoard, c).isWater)
			newGArmies[c] = gArmy
		self.garmies = newGArmies
