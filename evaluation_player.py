import pygame as pg
import board as b
from datatypes import Coord, Move

class EvaluationPlayer():
	ARMY_STRENGTH_WEIGHT = 0.4
	ARMY_MORALE_WEIGHT = 0.2
	STRENGTH_GEN_WEIGHT = 0.8

	def __init__(self, playerId):
		self.playerId = playerId

	# For a given board state, calculate the total power and total power generation for an army
	# Multiply each by some constant
	# Choose the move that maximizes this sum

	# returns: playerId -> (armyStrength, armyMorale, strengthGrowthPerTurn)
	def calculateBoardPowers(self, board) -> dict[int, (int, int, int)]:
		playerToPowers = {}
		for a in board.armies.values():
			playerPowers = playerToPowers.get(a.ownedBy, (0, 0, 0))
			newPlayerPowers = (playerPowers[0] + a.strength, playerPowers[1] + a.morale, playerPowers[2])
			playerToPowers[a.ownedBy] = newPlayerPowers
		for s in b.getAllSpaces(board):
			if s.ownedBy != -1:
				# Add space strength pool contribution for player
				spaceStrengthContribution = b.getSpaceStrengthContribution(s)
				playerPowers = playerToPowers.get(s.ownedBy, (0, 0, 0))
				newPlayerPowers = (playerPowers[0], playerPowers[1], playerPowers[2] + spaceStrengthContribution)
				playerToPowers[s.ownedBy] = newPlayerPowers 
		return playerToPowers

	# returns: playerId -> (change in armyPower, change in powerGrowthPerTurn)
	def calculateMovePowerChanges(self, board, move, currentPlayerToPowers) -> (int, int, int):
		newBoard = board
		if not move.isEndTurn:
			newBoard = b.moveArmy(newBoard, move.fromCoord, move.toCoord)
		newBoard = b.endTurn(newBoard, self.playerId)

		# TODO: Can reduce computation requirements by only looking at certain coords
		newPlayerToPowers = self.calculateBoardPowers(newBoard)
		netPowerChange = (0, 0, 0)
		for playerId, powers in currentPlayerToPowers.items():
			newPowers = newPlayerToPowers.get(playerId, (0, 0, 0))
			difference = (newPowers[0] - powers[0], newPowers[1] - powers[1], newPowers[2] - powers[2])
			if playerId == self.playerId:
				netPowerChange = (netPowerChange[0] + difference[0], netPowerChange[1] + difference[1], netPowerChange[2] + difference[2])
			else:
				netPowerChange = (netPowerChange[0] - difference[0], netPowerChange[1] - difference[1], netPowerChange[2] - difference[2])
		return netPowerChange


	def requestMove(self, board, movesLeft) -> (Move, dict[Move, int]):
		playerToPowers = self.calculateBoardPowers(board)
		movableArmies = list(b.getMovableArmies(board, self.playerId))
		moveEvaluations = {}

		bestChange = None
		bestMove = None
		for army in movableArmies:
			doNothingMove = Move(army.coord, army.coord, isEndTurn=True)
			netPowerChange = self.calculateMovePowerChanges(board, doNothingMove, playerToPowers)
			weightedChange = netPowerChange[0] * self.ARMY_STRENGTH_WEIGHT + netPowerChange[1] * self.ARMY_MORALE_WEIGHT + netPowerChange[2] * self.STRENGTH_GEN_WEIGHT
			moveEvaluations[doNothingMove] = round(weightedChange, 4)

			bestArmyMove = doNothingMove
			bestArmyChange = weightedChange

			availableMoveSpaces = b.getMovesForArmy(board, army.coord)
			for space in availableMoveSpaces:
				move = Move(fromCoord=army.coord, toCoord=space.coord)
				netPowerChange = self.calculateMovePowerChanges(board, move, playerToPowers)
				weightedChange = netPowerChange[0] * self.ARMY_STRENGTH_WEIGHT + netPowerChange[1] * self.ARMY_MORALE_WEIGHT + netPowerChange[2] * self.STRENGTH_GEN_WEIGHT
				moveEvaluations[move] = weightedChange
				if weightedChange > bestArmyChange:
					bestArmyMove = move
					bestArmyChange = weightedChange

			if bestArmyMove != doNothingMove and (bestChange is None or bestArmyChange > bestChange):
				bestMove = bestArmyMove
				bestChange = bestArmyChange

		if bestChange is None:
			bestMove = Move(None, None, isEndTurn=True)
		return (bestMove, moveEvaluations)