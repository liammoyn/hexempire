import board as b
from datatypes import Coord, Move

defaultPreferences = [1, 1, 1, 1, 0.5, 0.1, 0.9, 0.2, 0.5]
def getPreferenceIdFromVector(preferenceVector) -> str:
	return ",".join([ str(v) for v in preferenceVector ])

class ObjectivePlayer():
	maxObjectivesConsideredPerArmy = 5
	maxThreatObjectivesConsidered = 5
	maxDistanceForThreat = 3
	maxArmyPower = 198 # TODO: Get from board rather than computer
	highestScore = 100

	def __init__(self, playerId, preferenceVector = defaultPreferences):
		self.preferenceId = getPreferenceIdFromVector(preferenceVector)
		self.playerId = playerId
		# TODO: Make sure any tradeoffs are simplified

		self.powerAdvantageFactor 					= preferenceVector[0]
		self.powerDisadvantageFactor 				= preferenceVector[1]
		self.moveFactor 							= preferenceVector[2]
		self.valueFactor 							= preferenceVector[3]
		self.attackingObjectivePreference 			= preferenceVector[4]
		self.defenceValuePreference 				= preferenceVector[5]
		self.defenceUrgencyOverAccomplishablePref 	= preferenceVector[6]
		self.attackValuePreference 					= preferenceVector[7]
		self.threatDefenderPreference 				= preferenceVector[8] # How much do we trust our defence vs an enemy attack

		self.defendingObjectivePreference = 1 - self.attackingObjectivePreference

		self.defenceUrgencyPreference = (1 - self.defenceValuePreference) * self.defenceUrgencyOverAccomplishablePref
		self.defenceAccomplishablePreference = (1 - self.defenceValuePreference) * (1 - self.defenceUrgencyOverAccomplishablePref)
		self.attackAccomplishablePreference = 1 - self.attackValuePreference



	"""

A good move will make progress towards completing an objective
	- Progress increases ability to acomplish
An uncaptured objective can be:
	- A space that can be captured
A good uc objective is valuable
	- Increases production capacity of the owner
	This is constant for an objective throughout the game
A good uc objective is acomplishable
	- Few moves to reach
	- Has strength to take
	This changes every turn and depends on the army
Progress makes an uc objective more acomplishable
	- Is the objective more acomplishable after this move?
		- Consider change in strength
		- Consider distance
	- Incorporate birdseye distance into move score
		- Can add a bias value to break ties
	- Incorporate side objectives of capturing territory
		- Done by morale change?

A good captured objective can be:
	- A space that is already owned
A good c objective is valuable
	- Increases production capacity of the owner
A good c objective is urgent
	- Is being threatened by enemies
	- Does not have adequate defences
	Calculated based on enemy posing the maximum amount of threat vs the defending army
A good c objective is acomplishable
	- Few moves to reach
	- Have strength to reduce threat or increase defences
Progress makes a c objective less urgent or more accomplishable
	- Moves towards objective
	- Incr


Need to know:
x Pathing from any space to an objective point
	- Usually straightline / a-star pathing
	- Can include key points like ports
? Threat of losing captured objectives
	- Presense of enemy troops with strength
- How to calculate progress towards objective
- How to consolidate

How to prioritize moves?
- Prioritize objective<>Army combos first
- For highest score objective<>Army, then check all moves


Plan
	For each army, evaluate top X objectives
	For each uncaptured objective, score based on value and achievability
	For the highest scoring Army-Objective: Determine which move maximizes progress

	For each enemy army, check distance to all of our captured objectives
	For each captured objective, add some threat value for each enemy army
	When looping our own army, score captured objectives based on their threat
		Threat = distance * power?
		Should we consider our own defending army?
			We should, unless we are evaluating moves for the defender
	To determine a move for a captured space, move closer or attack an enemy

	"""

	# TODO: Maybe value accounting for distance to starting capital
	# TODO: Can cache these values for spaces in the beginning of the game
	def getObjectiveValuableScore(self, board, objectiveSpace) -> float:
		"""
		Returns: 0-highestScore for value of objective to player
		"""
		baseValue = (
			20 if objectiveSpace.isCapital else
			10 if objectiveSpace.isTown else
			8 if objectiveSpace.isPort else
			0
		)
		return self.highestScore * (baseValue / 20)

	def getPowerAdvantageScore(self, attackingArmy, defendingArmy) -> (float, float):
		"""
		Returns: 0-self.highestScore for advantage and -self.highestScore-0 for disandvantage for attacking army
		"""
		attackPower = 0
		defendPower = 0
		if attackingArmy is None:
			defendPower = self.maxArmyPower
		else:
			attackPower = attackingArmy.strength + attackingArmy.morale
		if defendingArmy is None:
			attackPower = self.maxArmyPower
		else:
			defendPower = defendingArmy.strength + defendingArmy.morale
		difference = attackPower - defendPower
		scaledDifference = self.highestScore * (difference / self.maxArmyPower)
		if scaledDifference > 0:
			return (scaledDifference, 0)
		else:
			return (0, scaledDifference)

	def getArmyPowerScore(self, army) -> float:
		"""
		Returns: 0-self.highestScore for power of this army
		"""
		basePower = army.strength + army.morale
		return self.highestScore * (basePower / self.maxArmyPower)


	def _getMoveClosenessScore(self, curSpace, objectiveCoord, dropoff, midpoint) -> float:
		"""
		dropoff: Scales how fast score drops off
		midpoint: Scales moves away that gives a half score
		Returns 0-10 value for moves needed to objective
		"""
		movesToObjective = curSpace.pointToMoves[objectiveCoord]
		if movesToObjective is None:
			return 0
		elif movesToObjective == 0:
			return self.highestScore
		birdseyeDistance = b.birdsEyeDistance(curSpace.coord, objectiveCoord)
		moveWithBias = movesToObjective + birdseyeDistance * 0.01
		moveScore = 1 / (1 + pow(dropoff, moveWithBias - midpoint))
		return moveScore * self.highestScore


	def getAttackClosenessScore(self, curSpace, objectiveCoord) -> float:
		return self._getMoveClosenessScore(curSpace, objectiveCoord, 2, 3)

	def getDefenceClosenessScore(self, curSpace, objectiveCoord) -> float: # TODO: Probably get rid of this function
		return self._getMoveClosenessScore(curSpace, objectiveCoord, 5, 2)

	def getThreatClosenessScore(self, curSpace, objectiveCoord) -> float:
		return self._getMoveClosenessScore(curSpace, objectiveCoord, 5, 2)



# =======================================================
# ============= Objective Score Calcs ===================
# =======================================================


	def getPreferencedValuableScore(self, board, objectiveSpace) -> float:
		"""
		Returns: 0-self.highestScore for valuableness of the objective considering self preferences
		"""
		objectiveValueScore = self.getObjectiveValuableScore(board, objectiveSpace)

		unscaledScore =  (
			objectiveValueScore * self.valueFactor
		)
		return unscaledScore

	def getPreferencedUrgencyScore(self, army, objectiveSpace, capturedObjectiveToThreat) -> float:
		threatScore = capturedObjectiveToThreat[objectiveSpace.coord]
		if army.coord == objectiveSpace.coord:
			# TODO: Urgency increase should be based on 1 / (1 - getThreatClosenessScore(moves=1))
			threatScore = min(threatScore * (1 / 0.83), self.highestScore)
		return threatScore


	def getPreferencedAccomplishableAttackScore(self, board, army, objectiveSpace) -> float:
		"""
		Returns 0-self.highestScore value for how accomplishable move is considering self preferences
		"""
		curSpace = b.getSpaceFromCoord(board, army.coord)
		defenceArmy = board.armies.get(objectiveSpace.coord, None)

		powerAdvantageScore, powerDisadvantageScore = self.getPowerAdvantageScore(army, defenceArmy)
		moveScore = self.getAttackClosenessScore(curSpace, objectiveSpace.coord)

		unscaledScore = (
			powerAdvantageScore * self.powerAdvantageFactor +		# powerAdvantageScore is 0 or positive
			powerDisadvantageScore * self.powerDisadvantageFactor + # powerDisadvantageScore is 0 or negative
			moveScore * self.moveFactor
		)
		return unscaledScore / 3

	def getPreferencedAccomplishableDefenceScore(self, board, army, objectiveSpace) -> float:
		curSpace = b.getSpaceFromCoord(board, army.coord)

		# Ignore army's power for now 
		moveScore = self.getDefenceClosenessScore(curSpace, objectiveSpace.coord)

		unscaledScore = (
			moveScore * self.moveFactor
		)
		return unscaledScore / 1

	def getOverallArmyObjectiveScore(self, board, army, objectiveCoord, capturedObjectiveToThreat) -> float:
		objectiveSpace = b.getSpaceFromCoord(board, objectiveCoord)
		overallScore = 0
		if objectiveSpace.ownedBy == self.playerId:
			preferenceValuableScore = self.getPreferencedValuableScore(board, objectiveSpace)
			preferencedUrgencyScore = self.getPreferencedUrgencyScore(army, objectiveSpace, capturedObjectiveToThreat)
			preferenceAccomplishableScore = self.getPreferencedAccomplishableDefenceScore(board, army, objectiveSpace)

			averageScore = (
				preferenceValuableScore * self.defenceValuePreference +
				preferencedUrgencyScore * self.defenceUrgencyPreference +
				preferenceAccomplishableScore * self.defenceAccomplishablePreference
			)
			# print(f"D[{objectiveCoord}]: {preferenceValuableScore} + {preferencedUrgencyScore} + {preferenceAccomplishableScore}")
			# print(f"D[{objectiveCoord}]: {preferenceValuableScore * self.defenceValuePreference} + {preferencedUrgencyScore * self.defenceUrgencyPreference} + {preferenceAccomplishableScore * self.defenceAccomplishablePreference} = {averageScore}")
			overallScore = averageScore * self.defendingObjectivePreference
		else:
			preferenceValuableScore = self.getPreferencedValuableScore(board, objectiveSpace)
			preferenceAccomplishableScore = self.getPreferencedAccomplishableAttackScore(board, army, objectiveSpace)

			averageScore = (
				preferenceValuableScore * self.attackValuePreference +
				preferenceAccomplishableScore * self.attackAccomplishablePreference
			)
			# print(f"A[{objectiveCoord}]: {preferenceValuableScore} + {preferenceAccomplishableScore}")
			# print(f"A[{objectiveCoord}]: {preferenceValuableScore * self.attackValuePreference} + {preferenceAccomplishableScore * self.attackAccomplishablePreference} = {averageScore}")
			overallScore = averageScore * self.attackingObjectivePreference
		return overallScore



# =======================================================
# ============== Threat Calculations ====================
# =======================================================

	def getInfluenceScore(self, board, army, objectiveCoord) -> float:
		"""
		Returns: 0-self.highestScore for the ability of this army to capture or defend the given objective
		"""
		armySpace = b.getSpaceFromCoord(board, army.coord)

		powerScore = self.getArmyPowerScore(army)
		moveScore = self.getThreatClosenessScore(armySpace, objectiveCoord)

		overallScore = powerScore * (moveScore / self.highestScore)
		return overallScore

	def getThreatToObjectiveScore(self, defenceFactor, attackFactor) -> float:
		"""
		Returns: 0-self.highestScore for the defence vs attack accounting for preferences
		"""
		if defenceFactor == 0:
			return self.highestScore
		preferencedAttack = attackFactor * (1 - self.threatDefenderPreference)
		preferencedDefence = defenceFactor * self.threatDefenderPreference
		# Avoid div by 0 errors
		finalFactor = 0.5 if (preferencedDefence == preferencedAttack) else preferencedAttack / (preferencedDefence + preferencedAttack)
		
		return self.highestScore * finalFactor


	def enemyArmyInRange(self, board, army, objectiveCoord) -> bool:
		movesToObjective = b.getSpaceFromCoord(board, army.coord).pointToMoves[objectiveCoord]
		return movesToObjective is not None and movesToObjective <= self.maxDistanceForThreat # TODO: Don't hardcode

	def getTotalPreferencedThreatScoreForObjective(self, board, objectiveCoord) -> float:
		"""
		Returns: 0-self.highestScore for threat posed to this objective
		"""
		armiesInRange = [ a for a in board.armies.values() if self.enemyArmyInRange(board, a, objectiveCoord) ]
		defenceFactor = 0
		attackFactor = 0
		for army in armiesInRange:
			influenceScore = self.getInfluenceScore(board, army, objectiveCoord)
			if army.ownedBy == self.playerId:
				defenceFactor += influenceScore
			else:
				attackFactor += influenceScore
		return self.getThreatToObjectiveScore(defenceFactor, attackFactor)


	def getCapturedObjectiveToThreatScore(self, board) -> dict[Coord, float]:
		"""
		Returns: ObjectiveCoord -> threat score
		threat score: 0-self.highestScore for threat to objective
		"""
		# Coord -> (attack power, defence power)
		ownedObjectiveCoordToAttackAndDefence = { s.coord: (0, 0) for s in b.getAllPointsOfInterest(board) if s.ownedBy == self.playerId }
		allArmiesAndSpaces = [ (a, b.getSpaceFromCoord(board, a.coord) ) for a in board.armies.values() ]
		for army, space in allArmiesAndSpaces:
			objectivesConsidered = 0
			for objectiveCoord in space.sortedPoints:
				if objectivesConsidered > self.maxThreatObjectivesConsidered:
					break
				objectivesConsidered += 1
				if objectiveCoord in ownedObjectiveCoordToAttackAndDefence and space.pointToMoves[objectiveCoord] is not None:
					influenceScore = self.getInfluenceScore(board, army, objectiveCoord)
					curAttack, curDefence = ownedObjectiveCoordToAttackAndDefence[objectiveCoord]
					if army.ownedBy == self.playerId:
						ownedObjectiveCoordToAttackAndDefence[objectiveCoord] = (curAttack, curDefence + influenceScore)
					else:
						ownedObjectiveCoordToAttackAndDefence[objectiveCoord] = (curAttack + influenceScore, curDefence)
		ownedObjectiveCoordToThreat = { c: self.getThreatToObjectiveScore(ad[1], ad[0]) for c, ad in ownedObjectiveCoordToAttackAndDefence.items() }
		return ownedObjectiveCoordToThreat


# =======================================================
# =========== Best Move for Objective ===================
# =======================================================


	# TODO: Use existing accomplishability to get delta rather than absolute
	def getBestProgressTowardsAttackObjective(self, board, moveSpaces, armyCoord, objectiveCoord) -> (Coord, dict[Move, float]):
		# For each possible move, determine change in accomplishability
		moveToScore = {}
		bestCoordScore = (None, 0)
		for space in moveSpaces:
			newBoard = b.moveArmy(board, armyCoord, space.coord, isComputerCheck=True)
			newAttackArmy = newBoard.armies.get(space.coord, None)
			if newAttackArmy is None or newAttackArmy.ownedBy != self.playerId:
				newAttackArmy = None
			newDefenceArmy = newBoard.armies.get(objectiveCoord, None)
			if newDefenceArmy is None or newDefenceArmy.ownedBy == self.playerId:
				newDefenceArmy = None

			powerAdvantageScore, powerDisadvantageScore = self.getPowerAdvantageScore(newAttackArmy, newDefenceArmy)
			moveScore = self.getAttackClosenessScore(space, objectiveCoord)

			newPreferencedAccomplishableScore = (
				powerAdvantageScore * self.powerAdvantageFactor +
				powerDisadvantageScore * self.powerDisadvantageFactor +
				moveScore * self.moveFactor
			) / 3
			moveToScore[Move(armyCoord, space.coord)] = newPreferencedAccomplishableScore
			if newPreferencedAccomplishableScore > bestCoordScore[1]:
				bestCoordScore = (space.coord, newPreferencedAccomplishableScore)
		return (bestCoordScore[0], moveToScore)


	def getBestProgressTowardsDefenceObjective(self, board, moveSpaces, armyCoord, objectiveCoord) -> (Coord, dict[Move, float]):
		# For each possible move, determine change in urgency
		moveToScore = {}
		threatBefore = self.getTotalPreferencedThreatScoreForObjective(board, objectiveCoord) # TODO: Can just use cached value?

		# No move score
		newBoard = b.endTurn(board, self.playerId, isComputerCheck=True) # TODO: Use a faster version of endTurn
		newThreat = self.getTotalPreferencedThreatScoreForObjective(newBoard, objectiveCoord)
		urgencyChange = threatBefore - newThreat # TODO: Scale urgency change to be 0-self.highestScore for prettier output
		moveToScore[Move(armyCoord, armyCoord)] = urgencyChange
		bestCoordScore = (None, urgencyChange)

		for space in moveSpaces:
			newBoard = b.moveArmy(board, armyCoord, space.coord, isComputerCheck=True)
			newBoard = b.endTurn(newBoard, self.playerId, isComputerCheck=True)

			newThreat = self.getTotalPreferencedThreatScoreForObjective(newBoard, objectiveCoord)
			urgencyChange = threatBefore - newThreat

			moveToScore[Move(armyCoord, space.coord)] = urgencyChange
			if urgencyChange > bestCoordScore[1]:
				bestCoordScore = (space.coord, urgencyChange)
		return (bestCoordScore[0], moveToScore)


	def getBestProgressTowardsObjective(self, board, moveSpaces, armyCoord, objectiveCoord) -> (Coord, dict[Move, float]):
		objectiveSpace = b.getSpaceFromCoord(board, objectiveCoord)
		if objectiveSpace.ownedBy == self.playerId:
			return self.getBestProgressTowardsDefenceObjective(board, moveSpaces, armyCoord, objectiveCoord)
		else:
			return self.getBestProgressTowardsAttackObjective(board, moveSpaces, armyCoord, objectiveCoord)



# =======================================================
# ================== Main Entry =========================
# =======================================================


	def requestMove(self, board, movesLeft) -> (Move, dict[Move, float]):
		movableArmies = list(b.getMovableArmies(board, self.playerId))
		moveEvaluations = {}
		objectiveEvaluations = {}
		armyObjectiveRankings = []
		capturedObjectiveToThreat = self.getCapturedObjectiveToThreatScore(board)

		for army in movableArmies:
			curSpace = b.getSpaceFromCoord(board, army.coord)
			objectivesConsidered = 0
			for objectiveCoord in curSpace.sortedPoints:
				if objectivesConsidered >= self.maxObjectivesConsideredPerArmy:
					break
				objectivesConsidered += 1
				overallScore = self.getOverallArmyObjectiveScore(board, army, objectiveCoord, capturedObjectiveToThreat)
				objectiveEvaluations[Move(army.coord, objectiveCoord)] = overallScore
				armyObjectiveRankings.append((army.coord, objectiveCoord, overallScore))
		sortedArmyObjectives = sorted(armyObjectiveRankings, key=lambda aor: aor[2], reverse=True)

		# TODO: Determine all moves for this turn instead of just one each call
		bestMove = None
		stayInPlaceArmies = set()
		allMoveEvaluations = {}
		for armyCoord, objectiveCoord, score in sortedArmyObjectives:
			if armyCoord in stayInPlaceArmies:
				continue
			availableMoveSpaces = b.getMovesForArmy(board, armyCoord)
			bestCoord, moveEvaluations = self.getBestProgressTowardsObjective(board, availableMoveSpaces, armyCoord, objectiveCoord)
			allMoveEvaluations = allMoveEvaluations | moveEvaluations
			if bestCoord is not None:
				bestMove = Move(armyCoord, bestCoord)
				break
			else:
				stayInPlaceArmies.add(armyCoord)

		if bestMove is None:
			bestMove = Move(None, None, isEndTurn=True)

		return (bestMove, moveEvaluations, objectiveEvaluations)
