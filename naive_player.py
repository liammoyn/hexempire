import board as b
from datatypes import Coord, Move

class NaivePlayer():
	def __init__(self, playerId):
		self.playerId = playerId

	def requestMove(self, board, movesLeft) -> (Move, dict[Move, int]):
		moves = []
		movableArmies = list(b.getMovableArmies(board, self.playerId))
		for _ in range(movesLeft):
			if len(movableArmies) == 0:
				break
			armyToMove = movableArmies[0]
			availableMoves = b.getMovesForArmy(board, armyToMove.coord)
			if len(availableMoves) == 0:
				continue
			spaceToMoveTo = availableMoves[0]
			move = Move(armyToMove.coord, spaceToMoveTo.coord)
			moves.append(move)
		evals = {moves[0]: 1}
		print(f"Decided on move: {moves[0]}")
		return (moves[0], evals)

	
