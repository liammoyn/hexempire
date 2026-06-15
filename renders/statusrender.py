import pygame as pg
from datatypes import PlayerColors, PlayerNames, GameProgress

class GStatus:
	def __init__(self, GAME_FONT, x, y, w, h):
		self.GAME_FONT = GAME_FONT
		self.pos = (x, y)
		self.size = (w, h)

	# status: datatypes.GameStatus
	def draw(self, screen, status):
		# State of game: {waiting to start, running, finished}
		# Players turn: number or color
		# Moves left
		playerColor = PlayerColors[status.currentTurn]
		playerName = PlayerNames[status.currentTurn]
		borderSize = 10

		sf = pg.Surface(self.size, pg.SRCALPHA)
		pg.draw.rect(sf, playerColor, ((0, 0), self.size))
		pg.draw.rect(sf, "white", ((borderSize, borderSize), pg.Vector2(self.size) - pg.Vector2(borderSize * 2, borderSize * 2)))

		if status.gameProgress == GameProgress.OVER:
			resultS, resultBB = self.GAME_FONT.render("{} Wins!".format(playerName), "black", 8)

			sf.blit(resultS, ((self.size[0] - resultBB.w) / 2, (self.size[1] - resultBB.h) / 2))
		else:
			turnS, turnBB = self.GAME_FONT.render("Turn: {}".format(playerName), "black", 8)
			moveS, moveBB = self.GAME_FONT.render("Moves Left: {}".format(status.movesLeft), "black", 8)

			sf.blit(turnS, (borderSize, borderSize + 2))
			sf.blit(moveS, (self.size[0] - borderSize - moveBB.w, borderSize + 2))

		screen.blit(sf, self.pos)