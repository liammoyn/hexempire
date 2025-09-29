import board as b
from boardrender import GBoard
from datatypes import GameStatus, Board, GameProgress, Move

class GameStateController():
	"""
	Controls the game state
		Board
		Player's turn
		Player's moves left
		Game is start, running, finished
	Takes moves from players and updates game state accordingly
		Knows which players are users and which computers and who's turn it is

Other class?
	Recieves a computer instance for each player
This class?
	Can be told to switch between a computer and user for any player at any point


	Begins in a start state where no moves are made
	Start game method switches to a running state where we continuously wait for computer/user moves
	Detects when the game is over and switches to a game over state where no moves are made
	"""

	MOVES_PER_TURN = 5

	# TODO: Move hex calculations into init
	# playerTypes: list[bool] - whether each player id is a user or a computer
	def __init__(self, GAME_FONT, clock, cols, rows, hexW, hexH, playerTypes, isStepping):
		self.GAME_FONT = GAME_FONT
		self.clock = clock
		self.cols = cols
		self.rows = rows
		self.hexW = hexW
		self.hexH = hexH

		self.isUserPlayer = playerTypes
		self.stepping = isStepping

		self.newGame()

	def newGame(self, waterLevel=None, portLevel=None, townLevel=None):
		print("STARTING NEW BOARD INIT")
		newBoard = b.initializeBoard(self.cols, self.rows, waterLevel=waterLevel, portLevel=portLevel, townLevel=townLevel)
		self.newGameSetBoard(newBoard)

	def newGameSetBoard(self, newBoard, moveCounter=0, playersTurn=0, movesLeft=1, gamestate=GameProgress.WAITING):
		self.board = newBoard
		self.gboard = GBoard(self.GAME_FONT, self.clock, self.board, self.hexW, self.hexH)

		self.moveCounter = moveCounter
		self.playersTurn = playersTurn
		self.movesLeft = movesLeft
		self.queuedMove = None
		self.gamestate = gamestate
		self.playersAlive = 0b1111 # TODO: Better end game handling
		self.movableArmies = b.getMovableArmies(self.board, self.playersTurn)
		self.selectedArmy = None
		self.movableSpaces = None
		self.updateHighlights()

	def getStatus(self) -> GameStatus:
		return GameStatus(self.board, self.gamestate, self.moveCounter, self.playersTurn, self.movesLeft)

	def getGameStateString(self):
		boardString = b.getBoardString(self.board)
		gameString = f"{self.moveCounter},{self.playersTurn},{self.movesLeft},{boardString}"
		return gameString

	def useGameStateString(self, gameStateString):
		moveCounter, playersTurn, movesLeft, boardString = gameStateString.split(",", 3)
		newBoard = b.getBoardFromString(boardString)
		self.newGameSetBoard(newBoard, int(moveCounter), int(playersTurn), int(movesLeft), GameProgress.RUNNING)

	def startGame(self):
		self.gamestate = GameProgress.RUNNING

	def endGame(self):
		self.gamestate = GameProgress.OVER
		winner = self.playersAlive.bit_length() - 1
		self.playersTurn = winner
		print("Winner: " + str(winner))

	def makeMove(self, move):
		self.moveCounter += 1
		if not move.isEndTurn:
			newBoard = b.moveArmy(self.board, move.fromCoord, move.toCoord)
			self.board = newBoard
			self.playersAlive = b.getPlayersAlive(newBoard)
			self.gboard.refreshBoardMove(newBoard, move.toCoord)	
			self.movableArmies = b.getMovableArmies(self.board, self.playersTurn)
			self.movesLeft = min(self.movesLeft - 1, len(self.movableArmies))
		else:
			self.movesLeft = 0

		if self.playersAlive.bit_count() == 1:
			self.endGame()
		elif self.movesLeft <= 0:
			self.endTurn()
		else:
			self.selectedArmy = None
			self.movableSpaces = None
			self.updateHighlights()

	def endTurn(self):
		newBoard = b.endTurn(self.board, self.playersTurn)
		self.board = newBoard
		self.gboard.refreshBoard(newBoard)
		self.incrementTurn()
		self.selectedArmy = None
		self.movableSpaces = None
		self.updateHighlights()

	def incrementTurn(self):
		self.playersTurn = (self.playersTurn + 1) % 4
		if self.playersAlive & (1 << self.playersTurn) == 0:
			self.incrementTurn()
		else:
			self.movableArmies = b.getMovableArmies(self.board, self.playersTurn)
			self.movesLeft = min(self.MOVES_PER_TURN, len(self.movableArmies))

	def updateHighlights(self):
		self.gboard.unhighlightAll()
		if self.selectedArmy == None:
			# Nothing selected => highlight movable armies
			for a in self.movableArmies:
				self.gboard.highlightArmy(a, True)
		else:
			# One army selected => highlight this army and movable spaces
			self.gboard.highlightArmy(self.selectedArmy, True)
			for c in self.movableCoords:
				self.gboard.highlightCoord(c, True)

	def handleStepForward(self):
		if self.stepping and self.queuedMove is not None:
			self.makeMove(self.queuedMove)
			self.queuedMove = None

	def toggleStepping(self):
		if self.stepping:
			self.handleStepForward()
			self.stepping = False
		else:
			self.stepping = True

	# TODO: Take list of moves?
	def handleComputerMove(self, move, fromPlayerId):
		if self.isUserPlayer[self.playersTurn] or self.playersTurn != fromPlayerId:
			return
		self.queuedMove = move
		if not self.stepping:
			self.makeMove(move)

	def handleComputerEvals(self, moveEvals, objectiveEvals, fromPlayerId):
		if self.isUserPlayer[self.playersTurn] or self.playersTurn != fromPlayerId:
			return
		self.gboard.handleComputerEvals(moveEvals, objectiveEvals)

	def handleUserEndTurn(self):
		if self.isUserPlayer[self.playersTurn]:
			self.makeMove(Move(None, None, isEndTurn=True))

	def handleUserClick(self, clickPos):
		if not self.isUserPlayer[self.playersTurn]:
			# Ignore clicks if it isn't the user's turn
			return
		clickedSpace = self.gboard.getSpaceAt(clickPos)
		clickedArmy = self.gboard.getArmyAt(clickPos)
		if clickedSpace is not None and self.gamestate != "End":
			hasSelected = self.selectedArmy is not None
			if not hasSelected and clickedArmy in self.movableArmies:
				# Selecting an army
				self.selectedArmy = clickedArmy
				possibleMoves = b.getMovesForArmy(self.board, clickedArmy.coord)
				self.movableCoords = [s.coord for s in possibleMoves]
				self.updateHighlights()
			elif hasSelected and clickedSpace.coord not in self.movableCoords:
				# Deselecting their army
				self.selectedArmy = None
				self.movableCoords = None
				self.updateHighlights()
			elif hasSelected and clickedSpace.coord in self.movableCoords:
				# Moving their army
				self.queuedMove = Move(self.selectedArmy.coord, clickedSpace.coord)
				self.makeMove(Move(self.selectedArmy.coord, clickedSpace.coord))


	def draw(self, vp, vpMousePos):
		self.gboard.draw(vp, vpMousePos)

