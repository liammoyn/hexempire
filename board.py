import dataclasses as dcs
import math
import re
import time
import random
import uuid
import functools
from datatypes import Coord, Board, Space, Army, PlayerColors, TL, TC, TR, BL, BC, BR

# TODO: Move to board params
moralBlockFactor = 0.75
capitalBaseStrength = 8
townBaseStrength = 6
portAddStrength = 6
spaceAddStrength = 0.25
armyStrengthCap = 99

townMoraleBoost = 5
portMoraleBoost = 5
capitalMoraleBoost = 20
casualtiesMoraleEffectFactor = 0.25
waitingMoralePenalty = 1


# ========================================
# ========== Utils Board Stuff ===========
# ========================================

def getCoordFromIdx(idx, cols, rows) -> Coord:
	col = idx % cols
	row = int(idx / cols)
	return Coord(col, row)

def getIdxFromCoord(coord, board) -> int:
	return coord.row * board.cols + coord.col

def isOnBoard(board, coord) -> bool:
	if (coord.row < 0 or coord.row >= board.rows):
		return False
	if (coord.col < 0 or coord.col >= board.cols):
		return False
	return True

def getSpaceFromCoord(board, coord) -> Space:
	return board.grid[getIdxFromCoord(coord, board)]

def getAllSpaces(board) -> list[Space]:
	return board.grid

# TODO: Make this mapping less bad
def incIdxToSide(idx) -> int:
	return (
		TL if idx == 0 else
		TC if idx == 1 else
		TR if idx == 2 else
		BR if idx == 3 else
		BC if idx == 4 else
		BL if idx == 5 else -1
	)

def getFixedNeighborCoords(curCoord) -> list[Coord]:
	isOdd = curCoord.col % 2 == 1
	isOddInc = 1 if isOdd else 0
	# Goes clockwise from top left
	incs = [
		[-1, -1 + isOddInc],
		[0, -1],
		[1, -1 + isOddInc],
		[1, 0 + isOddInc],
		[0, 1],
		[-1, 0 + isOddInc]
	]
	return [Coord(x[0] + curCoord.col, x[1] + curCoord.row) for x in incs]

def getNeighborCoords(board, curCoord) -> list[Coord]:
	coords = getFixedNeighborCoords(curCoord)
	return [c for c in coords if isOnBoard(board, c)]


def getNeighborSpaces(board, curSpace, pred=(lambda s, e: True)) -> list[Space]:
	return [nextSpace for coord in getNeighborCoords(board, curSpace.coord) if pred(curSpace, nextSpace := getSpaceFromCoord(board, coord))]

def get2NeighborSpaces(board, curSpace, isPassablePred, killsMovementPred) -> list[Space]:
	"""
	TODO: Maybe worth converting this to handle more than just 2 steps / or just making it less ugly
	Returns list of spaces that are within 2 spaces of the curSpace respecting isPassable and killsMovement preds.

	isPassablePred: (Starting Space, Current Space, Next Space) -> bool if can go from cur to next
	killsMovementPred: (Starting Space, Current Space, Next Space) -> bool if going from cur to next ends movement
	"""
	curCoord = curSpace.coord
	# Goes clockwise from top left
	evenIncs = [
		(-1, -1),
		(0, -1),
		(1, -1),
		(1, 0),
		(0, 1),
		(-1, 0)
	]
	oddIncs = [
		(-1, 0),
		(0, -1),
		(1, 0),
		(1, 1),
		(0, 1),
		(-1, 1)
	]
	allIncs = [evenIncs, oddIncs]
	incCounter = curCoord.col % 2
	coordsToReturn = set()
	for i, inc in enumerate(allIncs[incCounter]):
		nextCoord = Coord(inc[0] + curCoord.col, inc[1] + curCoord.row)
		if not isOnBoard(board, nextCoord):
			continue
		nextSpace = getSpaceFromCoord(board, nextCoord)
		isPassable = isPassablePred(curSpace, curSpace, nextSpace)
		if not isPassable:
			continue
		coordsToReturn.add(nextSpace.coord)
		killsMovement = killsMovementPred(board.armies, curSpace, nextSpace)
		if not killsMovement:
			nextIncs = allIncs[(incCounter + inc[0]) % 2]
			trimmedIncs = [nextIncs[i-1], nextIncs[i], nextIncs[(i+1) % len(nextIncs)]]
			for nextInc in trimmedIncs:
				next2Coord = Coord(nextInc[0] + nextCoord.col, nextInc[1] + nextCoord.row)
				if not isOnBoard(board, next2Coord):
					continue
				next2Space = getSpaceFromCoord(board, next2Coord)
				isPassable = isPassablePred(curSpace, nextSpace, next2Space)
				if isPassable:
					coordsToReturn.add(next2Space.coord)
	return [ getSpaceFromCoord(board, c) for c in coordsToReturn ]

def birdsEyeDistance(startCoord, endCoord) -> int:
	axialDistance = lambda a, b: (
		(abs(a[0] - b[0]) 
          + abs(a[0] + a[1] - b[0] - b[1])
          + abs(a[1] - b[1])) / 2
	)
	offsetToAxial = lambda c: (
		c.col,
		c.row - (c.col - c.col & 1) / 2
	)
	return axialDistance(offsetToAxial(startCoord), offsetToAxial(endCoord))

def getAllPointsOfInterest(board) -> list[Space]:
	return [ s for s in getAllSpaces(board) if s.isPort or s.isCapital or s.isTown ]

def updateBoard(board, space=None, armies=None, spaces=None) -> Board:
	newGrid = board.grid[:]
	if space is not None:
		if not isOnBoard(board, space.coord):
			raise IndexError("{} not on board r {} by c {}".format(space.coord, board.rows, board.cols))
		newGrid[getIdxFromCoord(space.coord, board)] = space
	if spaces is not None:
		for newSpace in spaces:
			newGrid[getIdxFromCoord(newSpace.coord, board)] = newSpace
	newArmies = board.armies
	if armies is not None:
		newArmies = armies
	return dcs.replace(board, grid=newGrid, armies=newArmies)


# ===========================================
# ========== Initalize Board Stuff ==========
# ===========================================


# (islands: List[(List[Inland coords], List[Coastal coords])], oceans: List[List[Ocean coord]])
def getGeoBodyCoords(board) -> (list[(list[Coord], list[Coord])], list[Coord]):
	# Each island's coastal coords are their own list
	seen = set()
	islands = []
	oceans = []
	for startSpace in board.grid:
		if startSpace.coord in seen:
			continue
		# New island or ocean
		isOcean = startSpace.isWater

		queue = [ startSpace ]
		inlands = []
		coastals = []
		ocean = []
		while len(queue) > 0:
			cur = queue.pop(0)
			if cur.coord in seen or cur.isWater != isOcean:
				continue
			seen.add(cur.coord)
			neighbors = getNeighborSpaces(board, cur)
			queue = queue + neighbors
			if isOcean:
				ocean.append(cur.coord)
			else:
				if all(not s.isWater for s in neighbors):
					inlands.append(cur.coord)
				else:
					coastals.append(cur.coord)
		if isOcean:
			oceans.append(ocean)
		else:
			islands.append((coastals, inlands))
	return (islands, oceans)

def seedWater(board, seed, dropoff = 0.6) -> Board:
	seen = { seed }
	queue = [(seed, 0)]
	while len(queue) > 0:
		[coord, depth] = queue.pop(0)
		seen.add(coord)
		isWater = True if random.random() < math.pow(dropoff, depth) else False
		if isWater:
			newSpace = dcs.replace(getSpaceFromCoord(board, coord), isWater=True)
			board = updateBoard(board, newSpace)
			for neighbor in getNeighborCoords(board, coord):
				if not neighbor in seen:
					queue.append((neighbor, depth + 1))
	return board

def addWater(board, waterLevel) -> Board:
	seedNum = int(board.rows * board.cols * waterLevel)
	seedRaw = [random.randint(0, board.cols * board.rows - 1) for _ in range(seedNum)]
	seeds = map(lambda i: getCoordFromIdx(i, board.cols, board.rows), seedRaw)
	for seed in seeds:
		board = seedWater(board, seed)
	return board

def getCapitalCoords(board) -> list[Coord]:
	rows = board.rows
	cols = board.cols
	return [
		Coord(1, 1),
		Coord(1, rows - 2),
		Coord(cols - 2, 1),
		Coord(cols - 2, rows - 2)
	]


def placeStartingCapitals(board) -> Board:
	capitalCoords = getCapitalCoords(board)
	for playerId, capitalCoord in enumerate(capitalCoords):
		capitalSpace = getSpaceFromCoord(board, capitalCoord)
		capitalSpace = dcs.replace(capitalSpace, isCapital=True, isWater=False, ownedBy=playerId, firstOwner=playerId)
		board = updateBoard(board, capitalSpace)
		for neighbor in getNeighborCoords(board, capitalCoord):
			neighborSpace = getSpaceFromCoord(board, neighbor)
			neighborSpace = dcs.replace(neighborSpace, isWater=False, ownedBy=playerId)
			board = updateBoard(board, neighborSpace)
	return board

def removeIslands(board) -> Board:
	for space in getAllSpaces(board):
		neighbors = getNeighborSpaces(board, space)
		if all(s.isWater != space.isWater for s in neighbors):
			newSpace = dcs.replace(space, isWater=(not space.isWater))
			board = updateBoard(board, newSpace)
	return board

def paintIslands(board) -> Board:
	islands, oceans = getGeoBodyCoords(board)
	newSpaces = []
	for idx, island in enumerate(islands):
		coastals, inlands = island
		for coord in coastals:
			space = getSpaceFromCoord(board, coord)
			borderIsWater = [ isOnBoard(board, c) and getSpaceFromCoord(board, c).isWater for c in getFixedNeighborCoords(coord) ]
			newSpace = dcs.replace(space, isCoastal=True, borderIsWater=borderIsWater)
			newSpaces.append(newSpace)
		for coord in inlands:
			space = getSpaceFromCoord(board, coord)
			borderIsWater = [ isOnBoard(board, c) and getSpaceFromCoord(board, c).isWater for c in getFixedNeighborCoords(coord) ]
			newSpace = dcs.replace(space, isInland=True, borderIsWater=borderIsWater)
			newSpaces.append(newSpace)
	for idx, ocean in enumerate(oceans):
		for coord in ocean:
			space = getSpaceFromCoord(board, coord)
			newSpace = dcs.replace(space)
			newSpaces.append(newSpace)
	return updateBoard(board, spaces=newSpaces)

# allcoastTiles: list[Coord]
# oceans: list[set[Coord]]
def splitCoasts(board, allCoastTiles, oceans) -> list[list[Coord]]:
	oceanCoasts = [[] for _ in oceans]
	for coastCoord in allCoastTiles:
		neighbors = getNeighborCoords(board, coastCoord)
		for idx, ocean in enumerate(oceans):
			if any(n in ocean for n in neighbors):
				# coastCoord shares border with ocean
				oceanCoasts[idx].append(coastCoord)
	return [oc for oc in oceanCoasts if len(oc) > 0]

# possibleCoords: List[Coord]
# cutoff: float
# eligibilityPred: (Board, Coord) -> bool
# getNewSpace: Space -> Space
# atLeast: int
def sampleCoords(board, possibleCoords, cutoff, eligibilityPred, getNewSpace, atLeast = 0) -> Board:
	coordToProb = {coord: random.random() for coord in possibleCoords}
	eligibleCoords = set([c for c in possibleCoords if eligibilityPred(board, c)])
	queueOfCoordProbs = sorted(coordToProb.items(), key=lambda it: it[1], reverse=True)

	numChosen = 0
	while len(queueOfCoordProbs) > 0:
		coord, prob = queueOfCoordProbs.pop(0)
		if not coord in eligibleCoords:
			continue
		if prob < cutoff and numChosen >= atLeast:
			break
		numChosen = numChosen + 1
		thisSpace = getSpaceFromCoord(board, coord)
		newSpace = getNewSpace(thisSpace)
		board = updateBoard(board, newSpace)
		eligibleCoords = { c for c in eligibleCoords if eligibilityPred(board, c) }
	return board

# coast: List[Coord]
def addPortsToCoast(board, coast, portLevel) -> Board:
	eligibilityPred = lambda b, c: not any(n.isPort for n in getNeighborSpaces(b, getSpaceFromCoord(b, c)))
	getNewSpace = lambda s: dcs.replace(s, isPort=True)
	return sampleCoords(board, coast, portLevel, eligibilityPred, getNewSpace, 1)

def addPorts(board, portLevel) -> Board:
	islands, oceans = getGeoBodyCoords(board)
	# oceans: List[Set[Coord]]
	oceans = [set(lo) for lo in oceans]
	for island in islands:
		coastals, inlands = island
		coasts = splitCoasts(board, coastals, oceans)
		for idx, coast in enumerate(coasts):
			board = addPortsToCoast(board, coast, portLevel)
	return board

def canPlaceTown(board, coord) -> bool:
	thisSpace = getSpaceFromCoord(board, coord)
	isNeighborsWithSettlement = any(n.isPort or n.isCapital or n.isTown for n in getNeighborSpaces(board, thisSpace))
	return not thisSpace.isCapital and not thisSpace.isPort and not isNeighborsWithSettlement

def addTowns(board, townLevel) -> Board:
	lands = [s.coord for s in getAllSpaces(board) if not s.isWater]
	eligibilityPred = canPlaceTown
	getNewSpace = lambda s: dcs.replace(s, isTown=True)
	return sampleCoords(board, lands, townLevel, eligibilityPred, getNewSpace, 0)

def addBorder(board, spacesInBorder, color) -> Board:
	newSpaces = []
	coordsInBorder = set([s.coord for s in spacesInBorder])
	for s in spacesInBorder:
		neighbors = getFixedNeighborCoords(s.coord)
		updatedBorderColors = s.borderColors[:]
		for idx, n in enumerate(neighbors):
			if n not in coordsInBorder:
				updatedBorderColors[incIdxToSide(idx)] = color
			else:
				updatedBorderColors[incIdxToSide(idx)] = None
		newSpace = dcs.replace(s, borderColors=updatedBorderColors)
		newSpaces.append(newSpace)
	board = updateBoard(board, spaces=newSpaces)
	return board

def addBorders(board) -> Board:
	allOwnedSpaces = [ s for s in getAllSpaces(board) if s.ownedBy >= 0]
	ownerIdToSpaces = {}
	for space in allOwnedSpaces:
		ownerIdToSpaces.setdefault(space.ownedBy, []).append(space)
	for ownerId, spaces in ownerIdToSpaces.items():
		# TODO: Don't encode color info in the board
		color = PlayerColors[ownerId % len(PlayerColors)]
		board = addBorder(board, spaces, color)
	return board

# TODO: Figure out this function
# def updateBorders(board, spacesToCheck) -> Board:
# 	"""
# 	Update boarders only between spaces both in spacesToCheck
# 	"""
# 	newSpaces = []
# 	coordToOwner = { s.coord: s.ownedBy for s in spacesToCheck }
# 	for s in spacesToCheck:
# 		ownerId = s.ownedBy
# 		neighbors = getFixedNeighborCoords(s.coord)
# 		updatedBorderColors = s.borderColors[:]
# 		for idx, n in enumerate(neighbors):
# 			if n not in coordToOwner:
# 				continue
# 			neighborId = coordToOwner[n]
# 			if neighborId != ownerId and ownerId:
# 				color = PlayerColors[ownerId % len(PlayerColors)]
# 				updatedBorderColors[incIdxToSide(idx)] = color
# 			else:
# 				updatedBorderColors[incIdxToSide(idx)] = None
# 		newSpace = dcs.replace(s, borderColors=updatedBorderColors)
# 		newSpaces.append(newSpace)
# 	return updateBoard(board, spaces=newSpaces)

def addArmies(board, numPlayers) -> Board:
	newBoard = board
	for playerId in range(numPlayers):
		newBoard = addTurnStrength(newBoard, playerId)
	return newBoard

def getAllNumMovesToPoint(board, goalSpace) -> list[int]:
	"""
	For the given goal space, return a list where each index corresponds to a space on the grid
	and the value is the number of moves needed to get to the goal space
	"""
	maxMoves = 8 # TODO: Best value for this?
	numMoves = [ None for _ in board.grid ]
	todo = [ (goalSpace, 0) ]
	while len(todo) > 0:
		curSpace, movesSoFar = todo.pop()
		idx = getIdxFromCoord(curSpace.coord, board)
		if (numMoves[idx] is None or numMoves[idx] > movesSoFar):
			numMoves[idx] = movesSoFar
		else:
			continue
		if movesSoFar < maxMoves:
			oneMoveReachables = get2NeighborSpaces(board, curSpace, isReverseMovablePred, killsMovementPred)
			for neighbor in oneMoveReachables:
				todo.append((neighbor, movesSoFar + 1))
	return numMoves

def buildMovesToPointGraph(board) -> list[dict[Coord, int]]:
	"""
	Returns a list of the same size as board.grid where each element is a dict of how many
	turns it will take to get from a this space to a new coord
	"""
	listOfCoordToMoves = [ {} for _ in board.grid ]
	allPointsOfInterest = getAllPointsOfInterest(board)
	for pointOfInterest in allPointsOfInterest:
		movesToPoint = getAllNumMovesToPoint(board, pointOfInterest)
		for idx, moves in enumerate(movesToPoint):
			listOfCoordToMoves[idx][pointOfInterest.coord] = moves
	return listOfCoordToMoves

def addPointToMoves(board) -> Board:
	movesToPoint = buildMovesToPointGraph(board)
	newSpaces = []
	for idx, pointToMoves in enumerate(movesToPoint):
		sortedPoints = list(map(lambda entry: entry[0], sorted(filter(lambda e: e[1] is not None, pointToMoves.items()), key=lambda entry: entry[1])))
		space = board.grid[idx]
		newSpace = dcs.replace(space, pointToMoves=pointToMoves, sortedPoints=sortedPoints)
		newSpaces.append(newSpace)
	return updateBoard(board, spaces=newSpaces)

def postBoardCreateSteps(board) -> Board:
	board = addBorders(board)
	board = addPointToMoves(board)
	return board

def createBoard(cols, rows, seed, waterLevel, portLevel, townLevel) -> Board:
	grid = [Space(getCoordFromIdx(idx, cols, rows), False) for idx in range(cols * rows)]
	board = Board(grid, cols, rows, {}, seed)
	board = addWater(board, waterLevel)
	board = placeStartingCapitals(board)
	board = removeIslands(board)
	board = paintIslands(board)
	board = addPorts(board, portLevel)
	board = addTowns(board, townLevel)
	board = addArmies(board, 4)
	return postBoardCreateSteps(board)

def initializeBoard(cols, rows, seed=None, waterLevel=None, portLevel=None, townLevel=None) -> Board:
	if seed is None:
		seed = int(time.time() * 256)
	if waterLevel is None:
		waterLevel=0.04
	if portLevel is None:
		portLevel=0.9
	if townLevel is None:
		townLevel=0.85
	random.seed(seed)
	print(seed)
	return createBoard(cols, rows, seed, waterLevel, portLevel, townLevel)


# ========================================
# ========== Update Board Stuff ==========
# ========================================

def updateOwned(board, coord, playerId, isComputerCheck=False) -> Board:
	newSpaces = []
	space = getSpaceFromCoord(board, coord)
	if not space.isWater:
		newSpace = dcs.replace(space, ownedBy=playerId)
		newSpaces.append(newSpace)

	canBeClaimed = lambda s: not (space.isWater or s.isWater or s.isTown or s.isCapital or s.isPort) and s.coord not in board.armies
	toClaim = [s for s in getNeighborSpaces(board, space) if canBeClaimed(s) and s.ownedBy != playerId]
	for s in toClaim:
		newSpace = dcs.replace(s, ownedBy=playerId)
		newSpaces.append(newSpace)
	capturingArmy = board.armies.get(coord, None)
	newArmies = board.armies.copy() # TODO: Inefficient
	if capturingArmy is not None:
		newMorale = min(capturingArmy.morale + len(toClaim), capturingArmy.strength)
		capturingArmy = dcs.replace(capturingArmy, morale=newMorale)
		newArmies[coord] = capturingArmy
	board = updateBoard(board, armies=newArmies, spaces=newSpaces)
	# Don't bother updating graphical borders for comptuers to check moves
	board = board if isComputerCheck else addBorders(board)
	return board

def isMovablePred(start, cur, next) -> bool:
	return (
		# Stays on land, or is on a port
		(not cur.isWater and (not next.isWater or cur.isPort)) or
		# Stays on water, or has just left land
		(cur.isWater and (next.isWater or start.isWater))
	)

def isReverseMovablePred(start, cur, next) -> bool:
	return (
		# Stays on land, or only moves a single space out of water
		(not cur.isWater and (not next.isWater or start == cur)) or
		# Stays on water, or comes from port
		(cur.isWater and (next.isWater or (next.isPort and start.isWater)))
	)

def killsMovementPred(armies, cur, next) -> bool:
	return (
		# Going from water to land
		(cur.isWater and not next.isWater) or
		# Entering a point of interest
		(next.isTown or next.isCapital or next.isPort) or
		# Attacking/Merging with army
		(next.coord in armies)
	)

def getMovesForArmy(board, onCoord) -> list[Space]:
	startSpace = getSpaceFromCoord(board, onCoord)
	return get2NeighborSpaces(board, startSpace, isMovablePred, killsMovementPred)


# playerIdToBaseAmount: { int: int }
def applyLocalMorale(board, baseCoord, playerIdToBaseAmount) -> Board:
	# Fan out from base coord keeping track of depth
	# For any army in playerIdToBaseAmount, apply getUpdatedMorale to morale
	getMoraleChange = lambda base, depth: base * (1 / (1 << depth)) # TODO: what should this be?
	getUpdatedMorale = lambda army, depth: min(max(army.morale + getMoraleChange(playerIdToBaseAmount.get(army.ownedBy, 0), depth), 0), army.strength)
	maxDepth = 10
	newArmies = board.armies.copy()
	seen = set()
	queue = [ (baseCoord, 0) ]
	while len(queue) > 0:
		curCoord, depth = queue.pop()
		if curCoord in seen:
			continue
		else:
			seen.add(curCoord)
		curArmy = newArmies.get(curCoord, None)
		if curArmy is not None and curArmy.ownedBy in playerIdToBaseAmount:
			newArmies[curCoord] = dcs.replace(curArmy, morale=getUpdatedMorale(curArmy, depth))
		if depth < maxDepth:
			neighborCoords = getNeighborCoords(board, curCoord)
			for nc in neighborCoords:
				queue.append((nc, depth + 1))
	return updateBoard(board, armies=newArmies)

# playerIdToAmount: { int: int }
def applyGlobalMorale(board, playerIdToAmount) -> Board:
	getUpdatedMorale = lambda army: min(max(army.morale + playerIdToAmount.get(army.ownedBy, 0), 0), army.strength)
	getUpdatedArmy = lambda army: dcs.replace(army, morale=getUpdatedMorale(army))
	newArmies = { c: getUpdatedArmy(a) for c, a in board.armies.items() }
	newBoard = updateBoard(board, armies=newArmies)
	return newBoard

def updateCaptureMorale(board, defendingSpace, incomingArmy) -> Board:
	newBoard = board
	moraleChange = (
		0 if defendingSpace.ownedBy == incomingArmy.ownedBy else
		townMoraleBoost if defendingSpace.isTown else
		portMoraleBoost if defendingSpace.isPort else
		capitalMoraleBoost if defendingSpace.isCapital else
		0
	)
	if moraleChange > 0:
		idToChange = {
			incomingArmy.ownedBy: moraleChange,
			defendingSpace.ownedBy: -1 * moraleChange
		}
		newBoard = applyGlobalMorale(board, idToChange)
	return newBoard

def moveArmy(board, fromCoord, toCoord, isComputerCheck=False) -> Board:
	newBoard = board
	newArmies = board.armies.copy()
	attackingArmy = board.armies[fromCoord]
	defendingArmy = board.armies.get(toCoord, None)
	defendingSpace = getSpaceFromCoord(board, toCoord)

	if defendingArmy is None:
		# 1. Attacker moving to an empty space
		# Move attacker to new coord
		del newArmies[fromCoord]
		newArmies[toCoord] = dcs.replace(attackingArmy, coord=toCoord, canMove=False)
		newBoard = updateBoard(newBoard, armies=newArmies)
		newBoard = updateCaptureMorale(newBoard, defendingSpace, attackingArmy)
	elif attackingArmy.ownedBy == defendingArmy.ownedBy:
		# 2. Attacker moving to reenforce their own army
		newAttackArmy, newDefendArmy = determineMergeOutcome(attackingArmy, defendingArmy)
		if newAttackArmy is None:
			del newArmies[fromCoord]
		else:
			newArmies[fromCoord] = dcs.replace(newAttackArmy, canMove=False)
		newArmies[toCoord] = dcs.replace(newDefendArmy, canMove=False)
		newBoard = updateBoard(newBoard, armies=newArmies)
	else:
		# 3. Attacker moving to attack an enemy
		# Calculate new values for each army
		winningArmy, casualties = determineFightOutcome(attackingArmy, defendingArmy)
		del newArmies[fromCoord]
		newArmies[toCoord] = dcs.replace(winningArmy, coord=toCoord, canMove=False)
		newBoard = updateBoard(newBoard, armies=newArmies)

		winnerId = winningArmy.ownedBy
		loserId = attackingArmy.ownedBy + defendingArmy.ownedBy - winnerId

		moraleChange = int(casualties * casualtiesMoraleEffectFactor)
		idsToMoraleChange = {
			winnerId: moraleChange,
			loserId: -1 * moraleChange
		}
		newBoard = applyLocalMorale(newBoard, toCoord, idsToMoraleChange)

		newBoard = updateCaptureMorale(newBoard, defendingSpace, winningArmy)

	newBoard = updateOwned(newBoard, toCoord, attackingArmy.ownedBy, isComputerCheck)

	return newBoard

# Takes an attacking and defending army
# Returns the resulting winning army and number of casualties from loser
def determineFightOutcome(attackArmy, defendArmy) -> (Army, int):
	attackPower = attackArmy.strength + attackArmy.morale
	defendPower = defendArmy.strength + defendArmy.morale

	strongerArmy = attackArmy if attackPower > defendPower else defendArmy
	weakerPower = min(attackPower, defendPower)
	casualties = defendArmy.strength if attackPower > defendPower else attackArmy.strength

	baseStrengthLoss = weakerPower * (1 - moralBlockFactor)
	baseMoraleLoss = weakerPower * moralBlockFactor
	totalMoraleLoss = min(baseMoraleLoss, strongerArmy.morale)
	totalStrengthLoss = baseStrengthLoss + baseMoraleLoss - totalMoraleLoss
	newStronger = dcs.replace(
		strongerArmy,
		strength=int(max(strongerArmy.strength - totalStrengthLoss, 1)), # Round up if less than 1
		morale=int(strongerArmy.morale - totalMoraleLoss)
	)
	return (newStronger, casualties)

# Takes a moving army and a friendly recieving army
# Returns the resulting two armies
def determineMergeOutcome(movingArmy, catchingArmy) -> (Army, Army):
	totalStrength = movingArmy.strength + catchingArmy.strength
	newCatchingStrength = min(totalStrength, armyStrengthCap)
	newMovingStrength = totalStrength - newCatchingStrength

	totalMorale = movingArmy.morale + catchingArmy.morale
	newCatchingMorale = int((newCatchingStrength / totalStrength) * totalMorale)
	newMovingMorale = totalMorale - newCatchingMorale

	# Moving army is always replaced for rendering reasons
	newMoveArmy = dcs.replace(movingArmy, aid=uuid.uuid4(), strength=newMovingStrength, morale=newMovingMorale)
	newCatchArmy = dcs.replace(catchingArmy, strength=newCatchingStrength, morale=newCatchingMorale)
	if newMovingStrength == 0:
		return (None, newCatchArmy)
	else:
		return (newMoveArmy, newCatchArmy)

def getPlayersAlive(board) -> int:
	playersAlive = 0b0000
	spawnSpaces = [s for s in getAllSpaces(board) if (s.isTown or s.isCapital) and s.ownedBy != -1]
	for s in spawnSpaces:
		playersAlive = playersAlive | (1 << s.ownedBy)
	for a in board.armies.values():
		playersAlive = playersAlive | (1 << a.ownedBy)
	return playersAlive


def getMovableArmies(board, ownedBy) -> set[Army]:
	return { a for a in board.armies.values() if a.ownedBy == ownedBy and a.canMove }

def getSpaceStrengthContribution(space) -> int:
	return (
		portAddStrength if space.isPort else
		capitalBaseStrength if space.isCapital else
		townBaseStrength if space.isTown else
		spaceAddStrength if not space.isWater else
		0
	)

def addTurnStrength(board, playerId) -> Board:
	# Calculate a pool of additional strength
	# Distribute pool evenly between towns and capitals ontop of space's base strength
	# Add morale in proportion to current morale
	# Cap strength at armyStrengthCap and forfeit any allocated strength
	newArmies = board.armies.copy()
	getStrengthForSpace = lambda s: (
		portAddStrength if s.isPort else
		spaceAddStrength
	)
	allOwnedSpaces = [ s for s in getAllSpaces(board) if s.ownedBy == playerId ]
	totalStrengthPool = functools.reduce(lambda t, s: t + getStrengthForSpace(s), allOwnedSpaces, 0.0)
	allSpawnLocations = [ s for s in allOwnedSpaces if s.isTown or s.isCapital ]
	if len(allSpawnLocations) > 0:
		bonusStrength = int(totalStrengthPool / len(allSpawnLocations))
		for space in allSpawnLocations:
			isNewArmy = space.coord not in board.armies
			army = board.armies.get(space.coord, Army(uuid.uuid4(), space.coord, playerId))
			baseStrength = (
				capitalBaseStrength if space.isCapital else
				townBaseStrength
			)
			addedStrength = baseStrength + bonusStrength
			newTotalStrength = min(army.strength + addedStrength, armyStrengthCap)

			# TODO: Maybe added morale should be based on comparative total strength?
			addedMorale = int((newTotalStrength - army.strength) * army.morale / army.strength)
			newTotalMorale = min(army.morale + addedMorale, newTotalStrength)
			if isNewArmy:
				newTotalMorale = baseStrength
			newArmies[space.coord] = dcs.replace(army, strength=newTotalStrength, morale=newTotalMorale)
	return updateBoard(board, armies=newArmies)

def addTurnMorale(board, playerId) -> Board:
	shouldReduceMoraleLambda = lambda a: a.ownedBy == playerId and a.canMove
	getReducedMoraleArmy = lambda a: dcs.replace(a, morale=max(a.morale - waitingMoralePenalty, 0))
	updatedArmies = { c: getReducedMoraleArmy(a) for c, a in board.armies.items() if shouldReduceMoraleLambda(a) }
	newArmies = board.armies | updatedArmies
	return updateBoard(board, armies=newArmies)

# TODO: Do something with isComputerCheck?
def endTurn(board, playerId, isComputerCheck=False) -> Board:
	newBoard = addTurnMorale(board, playerId)
	newBoard = addTurnStrength(newBoard, playerId)

	# Reset all piece's canMove
	newArmies = { c: dcs.replace(a, canMove=True) for c, a in newBoard.armies.items() }
	newBoard = updateBoard(newBoard, armies=newArmies)
	return newBoard

# ===========================================
# ========== Computer Helper Stuff ==========
# ===========================================

def getPlayerScores(board) -> dict[int, float]:
	"""
	For each player on the board, give a relative score between 0->1 for how well they are doing
	"""
	playerPoints = {
		0: 0,
		1: 0,
		2: 0,
		3: 0,
	}
	for s in getAllSpaces(board):
		if s.ownedBy >= 0:
			points = getSpaceStrengthContribution(s)
			playerPoints[s.ownedBy] += points
	for a in board.armies.values():
		points = a.strength / 6
		playerPoints[a.ownedBy] += points

	total = 0
	for v in playerPoints.values():
		total += v

	scores = {}
	for k, v in playerPoints.items():
		scores[k] = v / total

	return scores



# ========================================
# ========== Print Board Stuff ==========
# ========================================


def getBoardString(board) -> str:
	sizeStr = f"X[{board.cols},{board.rows}]"
	getGeoStr = lambda s: (
		"w" if s.isWater else
		"l" if s.isInland else
		"c" if s.isCoastal else
		"?"
	)
	getTypeStr = lambda s: (
		"c" if s.isCapital else
		"t" if s.isTown else
		"p" if s.isPort else
		"n"
	)
	gridStr = "G["
	for s in board.grid:
		spaceString = f"S({getGeoStr(s)},{getTypeStr(s)},{s.ownedBy},{s.firstOwner})"
		gridStr += spaceString
	gridStr += "]"
	armiesStr = "A["
	for a in board.armies.values():
		canMoveStr = "T" if a.canMove else "F"
		armyString = f"U({a.coord.col},{a.coord.row},{a.ownedBy},{a.strength},{a.morale},{canMoveStr})"
		armiesStr += armyString
	armiesStr += "]"
	seedString = f"D[{board.seed}]"
	return sizeStr + gridStr + armiesStr + seedString

def getBoardFromString(boardString) -> Board:
	print(boardString)
	sizeStr = re.search(r"X\[([^\]]+)\]", boardString).group(1)
	c, r = sizeStr.split(",")
	cols = int(c)
	rows = int(r)

	spaceList = []
	gridStr = re.search(r"G\[([^\]]+)\]", boardString).group(1)
	for idx, spaceStrFull in enumerate(re.finditer(r"S\(([^\)]+)\)", gridStr)):
		spaceStr = spaceStrFull.group(1)
		geoS, typeS, ownedBy, firstOwner = spaceStr.split(",")
		space = Space(
			getCoordFromIdx(idx, cols, rows),
			geoS == "w",
			typeS == "c",
			int(ownedBy),
			int(firstOwner),
			geoS == "c",
			geoS == "l",
			typeS == "p",
			typeS == "t"
		)
		spaceList.append(space)

	armyDict = {}
	armiesStr = re.search(r"A\[([^\]]+)\]", boardString).group(1)
	for armyStrFull in re.finditer(r"U\(([^\)]+)\)", armiesStr):
		armyStr = armyStrFull.group(1)
		col, row, ownedBy, strength, morale, canMove = armyStr.split(",")
		coord = Coord(int(col), int(row))
		canMoveB = canMove == "T"
		army = Army(uuid.uuid4(), coord, int(ownedBy), int(strength), int(morale), canMoveB)
		armyDict[coord] = army

	seedStr = re.search(r"D\[([^\]]+)\]", boardString).group(1)
	seed = int(seedStr)
	
	newBoard = Board(spaceList, cols, rows, armyDict, seed)
	return postBoardCreateSteps(newBoard)
