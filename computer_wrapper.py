import pygame as pg
import time
from datatypes import GameProgress

COMPUTER_MOVE_TYPE = pg.event.custom_type()
COMPUTER_EVALS_TYPE = pg.event.custom_type()

class ComputerWrapper():
	def __init__(self, player, playerId):
		self.player = player # class with requestMove(board) method
		self.playerId = playerId # playerId of this player

	def _postMove(self, move):
		eventAttributes = {
			"move": move,
			"playerId": self.playerId
		}
		moveEvent = pg.event.Event(COMPUTER_MOVE_TYPE, eventAttributes)
		pg.event.post(moveEvent)

	def _postEvaluations(self, moveEvaluations, objectiveEvaluations):
		eventAttributes = {
			"moveEvaluations": moveEvaluations,
			"objectiveEvaluations": objectiveEvaluations,
			"playerId": self.playerId
		}
		event = pg.event.Event(COMPUTER_EVALS_TYPE, eventAttributes)
		pg.event.post(event)

	# Will be run in its own thread
	def startGameThinking(self, statusQueue):
		while True:
			gameStatus = statusQueue.get()
			if gameStatus.gameProgress == GameProgress.OVER:
				break
			if gameStatus.currentTurn == self.playerId:
				move, moveEvaluations, objectiveEvaluations = self.player.requestMove(gameStatus.board, gameStatus.movesLeft)
				self._postMove(move)
				self._postEvaluations(moveEvaluations, objectiveEvaluations)


