class ComputerWrapper():
	def __init__(self, player, playerId):
		self.player = player
		self.playerId = playerId

	def requestMove(self, board, movesLeft):
		return self.player.requestMove(board, movesLeft)
