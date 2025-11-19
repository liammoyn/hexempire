import pygame as pg
from hexutils import calculateHexPosition, hexGeomertry

class GEval():
	def __init__(self, GAME_FONT, w, h, fromCoord, coordWithEvals, moveEvRange, objectiveEvRange):
		self.GAME_FONT = GAME_FONT
		self.w = w
		self.h = h
		pos, center = calculateHexPosition(fromCoord.col, fromCoord.row, w, h)
		self.pos = pos
		self.center = center
		geometry = hexGeomertry(w, h)
		self.geometry = geometry
		self.centerPoints = [(p[0] + pos[0], p[1] + pos[1]) for p in geometry.points]

		toCoordToPos = {}
		toCoordToPoints = {}
		for toCoord, _, _ in coordWithEvals:
			toPos, toCenter = calculateHexPosition(toCoord.col, toCoord.row, w, h)
			toPoints = [(p[0] + toPos[0], p[1] + toPos[1]) for p in geometry.points]
			toCoordToPos[toCoord] = toPos
			toCoordToPoints[toCoord] = toPoints
		self.toCoordToPos = toCoordToPos
		self.toCoordToPoints = toCoordToPoints

		self.coordWithEvals = coordWithEvals
		self.moveEvRange = moveEvRange
		self.objectiveEvRange = objectiveEvRange

	def draw(self, screen):
		for toCoord, moveEv, objectiveEv in self.coordWithEvals:
			pos = self.toCoordToPos[toCoord]
			
			sf = pg.Surface((self.w, self.h), pg.SRCALPHA)
			text = ""

			if moveEv is not None and objectiveEv is not None:
				moveColor = calculateColor(moveEv, self.moveEvRange)
				pg.draw.polygon(sf, moveColor, self.geometry.points[3:6] + self.geometry.points[0:1])
				objColor = calculateColor(objectiveEv, self.objectiveEvRange)
				pg.draw.polygon(sf, objColor, self.geometry.points[0:4])
				pg.draw.polygon(sf, "yellow", self.geometry.points[0:4], 2)

				text = f"{int(round(moveEv))}/{int(round(objectiveEv))}"
			elif moveEv is not None:
				moveColor = calculateColor(moveEv, self.moveEvRange)
				pg.draw.polygon(sf, moveColor, self.geometry.points)
				text = str(round(moveEv, 1))
			elif objectiveEv is not None:
				objColor = calculateColor(objectiveEv, self.objectiveEvRange)
				pg.draw.polygon(sf, objColor, self.geometry.points)
				pg.draw.polygon(sf, "yellow", self.geometry.points, 2)
				text = str(round(objectiveEv, 1))


			tsf = drawEvalText(self.w, self.h, self.GAME_FONT, text)
			screen.blit(sf, pos)
			screen.blit(tsf, pos)


def calculateColor(ev, evRange):
	minScore = evRange[0]
	maxScore = evRange[1]
	midScore = (maxScore + minScore) / 2
	alpha = 150
	bestColor = pg.Color(0, 255, 0, alpha)
	worstColor = pg.Color(255, 0, 0, alpha)
	baseColor = pg.Color(255, 255, 255, alpha)
	if ev > midScore:
		factor = (ev - midScore) / (maxScore - midScore)
		return baseColor.lerp(bestColor, factor)
	elif ev < midScore:
		factor = (midScore - ev) / (midScore - minScore)
		return baseColor.lerp(worstColor, factor)
	else:
		return baseColor

def drawEvalText(w, h, font, text):
	sf = pg.Surface((w, h), pg.SRCALPHA)
	textColor = (0, 0, 0, 150)
	text_surface, text_rect = font.render(text, fgcolor=textColor, size=int(w * .23))
	txp = (w - text_rect.width) / 2
	typ = (h - text_rect.height) / 2
	sf.blit(text_surface, (txp, typ))
	return sf
