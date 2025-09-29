import board as b
import time
import cProfile
from datatypes import GameStatus, Board, GameProgress, Move
from objective_player import ObjectivePlayer

class ComputerGameRunner():
	"""
	Contains all the logic to run a game between computers and produce the winner
	Does not render anything to the screen
	"""
	MOVES_PER_TURN = 5
	MAX_MOVES_PER_GAME = 200
	MAX_SECONDS_PER_GAME = 300

	def __init__(self, players, board):
		self.computerPlayers = players
		self.board = board
		self.playerIdToScore = {}

		self.moveCounter = 0
		self.playersTurn = 0
		self.movesLeft = 1
		self.gamestate = GameProgress.RUNNING
		self.playersAlive = 0b1111
		self.movableArmies = b.getMovableArmies(self.board, self.playersTurn)


	def runGame(self) -> dict[int, float]:
		"""
		Runs a game between the players and returns a score for each player for how well they performed
		"""
		lastMoveCounter = None
		gameStatus = self.getStatus()
		timeStarted = time.time()
		while gameStatus.gameProgress != GameProgress.OVER and time.time() < (timeStarted + self.MAX_SECONDS_PER_GAME) and gameStatus.moveCounter < self.MAX_MOVES_PER_GAME:
			gameStatus = self.getStatus()

			if gameStatus.moveCounter != lastMoveCounter:
				playerId = gameStatus.currentTurn
				player = self.computerPlayers[playerId]
				move, moveEvaluations, objectiveEvaluations = player.requestMove(gameStatus.board, gameStatus.movesLeft)

				self.makeMove(move)

				lastMoveCounter = gameStatus.moveCounter


		if gameStatus.gameProgress != GameProgress.OVER:
			self.populateHoldoutScores()

		return self.playerIdToScore

	def getRound(self) -> int:
		return int(self.moveCounter / 4) + 1

	def getStatus(self) -> GameStatus:
		return GameStatus(self.board, self.gamestate, self.moveCounter, self.playersTurn, self.movesLeft)

	def populateHoldoutScores(self):
		playerScores = b.getPlayerScores(self.board)
		for playerId in range(4):
			isPlayerAlive = (1 << playerId) & self.playersAlive > 0
			if isPlayerAlive:
				score = playerScores[playerId]
				# TODO: Score should be between 0-1
				self.playerIdToScore[playerId] = score

	def assignLoserScore(self, playerId):
		self.playerIdToScore[playerId] = -1 * ((self.MAX_MOVES_PER_GAME / 4) - self.getRound())

	def assignWinnerScore(self, palyerId):
		self.playerIdToScore[palyerId] = (self.MAX_MOVES_PER_GAME / 4) - self.getRound()


	def makeMove(self, move):
		self.moveCounter += 1
		if not move.isEndTurn:
			newBoard = b.moveArmy(self.board, move.fromCoord, move.toCoord, isComputerCheck=True)
			self.board = newBoard
			newPlayersAlive = b.getPlayersAlive(newBoard)
			if newPlayersAlive != self.playersAlive:
				deadPlayer = (~newPlayersAlive & self.playersAlive).bit_length() - 1
				self.assignLoserScore(deadPlayer)
				self.playersAlive = newPlayersAlive
			self.movableArmies = b.getMovableArmies(self.board, self.playersTurn)
			self.movesLeft = min(self.movesLeft - 1, len(self.movableArmies))
		else:
			self.movesLeft = 0

		if self.playersAlive.bit_count() == 1:
			self.endGame()
		elif self.movesLeft <= 0:
			self.endTurn()

	def endTurn(self):
		newBoard = b.endTurn(self.board, self.playersTurn, isComputerCheck=True)
		self.board = newBoard
		self.incrementTurn()

	def incrementTurn(self):
		self.playersTurn = (self.playersTurn + 1) % 4
		if self.playersAlive & (1 << self.playersTurn) == 0:
			self.incrementTurn()
		else:
			self.movableArmies = b.getMovableArmies(self.board, self.playersTurn)
			self.movesLeft = min(self.MOVES_PER_TURN, len(self.movableArmies))

	def endGame(self):
		self.gamestate = GameProgress.OVER
		winner = self.playersAlive.bit_length() - 1
		self.assignWinnerScore(winner)
		self.playersTurn = winner

def main():
	players = [ ObjectivePlayer(i) for i in range(4) ]
	board = b.initializeBoard(12, 8)
	gameRunner = ComputerGameRunner(players, board)
	finalGameStatus = gameRunner.runGame()
	print(finalGameStatus)

if __name__ == '__main__':
	main()
	# cProfile.run('main()')
