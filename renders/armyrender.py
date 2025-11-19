import pygame as pg
import pygame.freetype as ft
from pygame.math import lerp
from hexutils import calculateHexPosition
from datatypes import PlayerColors
from renders.animationconstants import INFO_FADE_TIME, MOVE_TIME, BOOM_TIME, MOVE_BOOM_OVERLAP_TIME, APPEAR_TIME

class GArmy:
	def __init__(self, FONT, clock, army, c, r, w, h):
		self.FONT = FONT
		self.clock = clock
		self.army = army
		pos, center = calculateHexPosition(c, r, w, h)
		self.pos = pos
		self.center = center
		self.w = w
		self.h = h
		self.startAppear = 0
		self.startFade = 0
		self.startMove = -1
		self.targetPos = pos

		self.startDeath = -1
		self.totalDeathTime = MOVE_TIME
		self.isFinished = False

	def beginMove(self, newCoord):
		newPos, newCenter = calculateHexPosition(newCoord.col, newCoord.row, self.w, self.h)
		self.targetPos = newPos
		self.center = newCenter
		self.startMove = 0

	def beginDeath(self, newCoord, shouldExplode):
		# Start move to target pos
		# After move is done:
		# If shouldExplode, start explosion
		# After explosion finishes, isFinished = True
		self.startDeath = 0
		self.beginMove(newCoord)
		if shouldExplode:
			self.totalDeathTime += BOOM_TIME - MOVE_BOOM_OVERLAP_TIME

	def refreshArmy(self, newArmy, onWater):
		if newArmy.coord != self.army.coord:
			self.beginMove(newArmy.coord)
		self.army = newArmy
		self.onWater = onWater

	# Returns real pos
	# TODO: Consider keeping speed constant rather than time
	def handleMove(self) -> (float, float):
		if self.startMove >= 0: # Increment moveClock if moving
			self.startMove += self.clock.get_time()
		if self.startMove > MOVE_TIME: # End moveClock if finished moving
			self.pos = self.targetPos
			self.startMove = -1
		realPos = self.pos
		if self.startMove >= 0: # Interpolate position if moving
			progress = self.startMove / MOVE_TIME
			realPos = (snapInterp(self.pos[0], self.targetPos[0], progress), snapInterp(self.pos[1], self.targetPos[1], progress))
		return realPos


	def draw(self, screen, showNumber):
		appearOffset = 0
		if self.startAppear >= 0:
			self.startAppear += self.clock.get_time()
		if self.startAppear > APPEAR_TIME:
			self.startAppear = -1
		if self.startAppear >= 0:
			# Rise from the ground
			progress = self.startAppear / APPEAR_TIME
			appearOffset = snapInterp(self.h, 0, progress)

		realPos = self.handleMove()

		if self.startDeath >= 0:
			self.startDeath += self.clock.get_time()

		if self.startDeath > self.totalDeathTime:
			# totalDeathTime < startDeath => Don't render anything
			self.isFinished = True
		elif self.startDeath > MOVE_TIME - MOVE_BOOM_OVERLAP_TIME:
			# moveTime < startDeath < totalDeathTime => Render a boom
			sf = drawBoom(self.w, self.h, self.startDeath - (MOVE_TIME - MOVE_BOOM_OVERLAP_TIME), BOOM_TIME)
			screen.blit(sf, pg.Vector2(realPos) - pg.Vector2(self.w / 2, self.h / 2))
		else:
			# startDeath < moveTime: Render normally
			armySf = None
			armyColor = PlayerColors[self.army.ownedBy] if self.army.ownedBy != -1 else "black"
			if self.army.strength < 35:
				armySf = drawSmallNavalArmy(self.w, self.h, armyColor) if self.onWater else drawSmallArmy(self.w, self.h, armyColor)
			elif self.army.strength < 70:
				armySf = drawMediumNavalArmy(self.w, self.h, armyColor) if self.onWater else drawMediumArmy(self.w, self.h, armyColor)
			else:
				armySf = drawLargeNavalArmy(self.w, self.h, armyColor) if self.onWater else drawLargeArmy(self.w, self.h, armyColor)

			bottomMask = pg.Surface((self.w, self.h * 0.9), pg.SRCALPHA)
			bottomMask.blit(armySf, (0, appearOffset))
			screen.blit(bottomMask, realPos)

			if showNumber:
				self.startFade += self.clock.get_time()
				sf = drawText(self.w, self.h, self.army, self.FONT, self.startFade, INFO_FADE_TIME)
				screen.blit(sf, realPos)
			else:
				self.startFade = 0

def snapInterp(start, end, progress) -> float:
	distance = end - start
	# dfactor goes from 0 to 1 for progress 0 to 1
	dfactor = 1 + (progress - 1) ** 3
	return start + (distance * dfactor)

def drawBoom(w, h, startBoom, boomTime):
	sf = pg.Surface((w * 2, h * 2), pg.SRCALPHA) # TODO: Maybe make bigger
	progress = startBoom / boomTime
	color = (255, lerp(255, 0, progress), lerp(255, 0, progress), 255)
	size = lerp(0, w, progress)
	pg.draw.circle(sf, color, (w, h), size)
	return sf

def drawText(w, h, army, font, startFade, fadeTime):
	sf = pg.Surface((w, h), pg.SRCALPHA)
	alpha = 255 * min(startFade / fadeTime , 1)
	mcolor = (255, 255, 255, alpha)
	scolor = (255, 0, 0, alpha)
	outlinecolor = (0, 0, 0, alpha)

	lineStart = (w * 0.2, h * 1)
	lineEnd = (w * 0.8, h * 0)
	circlePos = pg.Vector2(w / 2, h / 2)
	circleRad = h / 3

	pg.draw.circle(sf, mcolor, circlePos, circleRad)

	firstSf = pg.Surface((w, h), pg.SRCALPHA)
	pg.draw.circle(firstSf, scolor, circlePos, circleRad)
	pg.draw.polygon(firstSf, (255, 255, 255, 0), (lineStart, lineEnd, (w, h)))
	sf.blit(firstSf, (0, 0))

	pg.draw.circle(sf, outlinecolor, circlePos, circleRad, 2)
	pg.draw.line(sf, outlinecolor, lineStart, lineEnd, 3)

	maskSf = pg.Surface((w, h), pg.SRCALPHA)
	pg.draw.circle(maskSf, (255, 255, 255, 255), circlePos, circleRad)
	sf.blit(maskSf, (0, 0), special_flags=pg.BLEND_RGBA_MIN)

	textSize = int(w * 0.2)

	stext = str(army.strength)
	stext_surface, stext_rect = font.render(stext, fgcolor=(mcolor), size=textSize, style=ft.STYLE_STRONG)
	spos = (
		(w * 0.50 - stext_rect.width),
		(h * 0.48 - stext_rect.height)
	)
	sf.blit(stext_surface, spos)

	mtext = str(army.morale)
	mtext_surface, mtext_rect = font.render(mtext, fgcolor=(scolor), size=textSize, style=ft.STYLE_STRONG)
	mpos = (
		(w * 0.72 - mtext_rect.width),
		(h * 0.70 - mtext_rect.height)
	)
	sf.blit(mtext_surface, mpos)
	
	return sf

def drawSmallArmy(w, h, color) -> pg.Surface:
	sf = pg.Surface((w, h), pg.SRCALPHA)
	bodyPoints = [
		(w * 0.47,	h * 0.74),
		(w * 0.47,	h * 0.36),
		(w * 0.53,	h * 0.36),
		(w * 0.53,	h * 0.74)
	]
	pg.draw.polygon(sf, "black", bodyPoints, 2)
	pg.draw.polygon(sf, color, bodyPoints)
	pg.draw.circle(sf, color, (w * 0.5, h * 0.35), h * 0.15)
	pg.draw.circle(sf, "black", (w * 0.5, h * 0.35), h * 0.15, 1)
	return sf

def drawMediumArmy(w, h, color) -> pg.Surface:
	sf = pg.Surface((w, h), pg.SRCALPHA)
	armPoints = [
		(w * 0.3,	h * 0.53),
		(w * 0.3,	h * 0.47),
		(w * 0.7,	h * 0.47),
		(w * 0.7,	h * 0.53)
	]
	pg.draw.polygon(sf, "black", armPoints, 2)
	pg.draw.polygon(sf, color, armPoints)
	bodyPoints = [
		(w * 0.45,	h * 0.85),
		(w * 0.45,	h * 0.3),
		(w * 0.55,	h * 0.3),
		(w * 0.55,	h * 0.85)
	]
	pg.draw.polygon(sf, "black", bodyPoints, 2)
	pg.draw.polygon(sf, color, bodyPoints)
	pg.draw.circle(sf, color, (w * 0.5, h * 0.3), h * 0.15)
	pg.draw.circle(sf, "black", (w * 0.5, h * 0.3), h * 0.15, 1)
	return sf

def drawLargeArmy(w, h, color) -> pg.Surface:
	sf = pg.Surface((w, h), pg.SRCALPHA)
	leftArmPoints = [
		(w * 0.30,	h * 0.75),
		(w * 0.30,	h * 0.40),
		(w * 0.40,	h * 0.40),
		(w * 0.40,	h * 0.75)
	]
	pg.draw.polygon(sf, "black", leftArmPoints, 2)
	pg.draw.polygon(sf, color, leftArmPoints)
	rightArmPoints = [
		(w * 0.60,	h * 0.75),
		(w * 0.60,	h * 0.40),
		(w * 0.70,	h * 0.40),
		(w * 0.70,	h * 0.75)
	]
	pg.draw.polygon(sf, "black", rightArmPoints, 2)
	pg.draw.polygon(sf, color, rightArmPoints)
	bodyPoints = [
		(w * 0.42,	h * 0.85),
		(w * 0.42,	h * 0.3),
		(w * 0.58,	h * 0.3),
		(w * 0.58,	h * 0.85)
	]
	pg.draw.polygon(sf, "black", bodyPoints, 2)
	pg.draw.polygon(sf, color, bodyPoints)
	pg.draw.circle(sf, color, (w * 0.5, h * 0.3), h * 0.15)
	pg.draw.circle(sf, "black", (w * 0.5, h * 0.3), h * 0.15, 1)
	return sf

def drawSmallNavalArmy(w, h, color) -> pg.Surface:
	sf = pg.Surface((w, h), pg.SRCALPHA)
	mastPoints = [
		(w * 0.52,	h * 0.54),
		(w * 0.48,	h * 0.54),
		(w * 0.48,	h * 0.30),
		(w * 0.52,	h * 0.30)
	]
	pg.draw.polygon(sf, "black", mastPoints, 2)
	pg.draw.polygon(sf, color, mastPoints)
	sailPoints = [
		(w * 0.50,	h * 0.46),
		(w * 0.65,	h * 0.41),
		(w * 0.50,	h * 0.30)
	]
	pg.draw.polygon(sf, "black", sailPoints, 2)
	pg.draw.polygon(sf, color, sailPoints)
	bodyPoints = [
		(w * 0.45,	h * 0.68),
		(w * 0.38,	h * 0.65),
		(w * 0.33,	h * 0.58),
		(w * 0.30,	h * 0.52),
		(w * 0.70,	h * 0.52),
		(w * 0.67,	h * 0.58),
		(w * 0.62,	h * 0.65),
		(w * 0.55,	h * 0.68),
	]
	pg.draw.polygon(sf, "black", bodyPoints, 2)
	pg.draw.polygon(sf, color, bodyPoints)
	return sf


def drawMediumNavalArmy(w, h, color) -> pg.Surface:
	sf = pg.Surface((w, h), pg.SRCALPHA)
	stack1Points = [
		(w * 0.34,	h * 0.54),
		(w * 0.37,	h * 0.54),
		(w * 0.37,	h * 0.40),
		(w * 0.34,	h * 0.40)
	]
	pg.draw.polygon(sf, "black", stack1Points, 2)
	pg.draw.polygon(sf, color, stack1Points)
	stack2Points = [
		(w * 0.45,	h * 0.54),
		(w * 0.48,	h * 0.54),
		(w * 0.48,	h * 0.40),
		(w * 0.45,	h * 0.40)
	]
	pg.draw.polygon(sf, "black", stack2Points, 2)
	pg.draw.polygon(sf, color, stack2Points)
	stack3Points = [
		(w * 0.58,	h * 0.54),
		(w * 0.61,	h * 0.54),
		(w * 0.61,	h * 0.40),
		(w * 0.58,	h * 0.40)
	]
	pg.draw.polygon(sf, "black", stack3Points, 2)
	pg.draw.polygon(sf, color, stack3Points)
	bodyPoints = [
		(w * 0.30,	h * 0.70),
		(w * 0.27,	h * 0.65),
		(w * 0.26,	h * 0.60),
		(w * 0.25,	h * 0.52),
		(w * 0.75,	h * 0.52),
		(w * 0.72,	h * 0.60),
		(w * 0.68,	h * 0.65),
		(w * 0.62,	h * 0.70),
	]
	pg.draw.polygon(sf, "black", bodyPoints, 2)
	pg.draw.polygon(sf, color, bodyPoints)
	return sf


def drawLargeNavalArmy(w, h, color) -> pg.Surface:
	sf = pg.Surface((w, h), pg.SRCALPHA)
	stack1Points = [
		(w * 0.28,	h * 0.54),
		(w * 0.41,	h * 0.54),
		(w * 0.37,	h * 0.34),
		(w * 0.28,	h * 0.34)
	]
	pg.draw.polygon(sf, "black", stack1Points, 2)
	pg.draw.polygon(sf, color, stack1Points)
	stack2Points = [
		(w * 0.28,	h * 0.54),
		(w * 0.45,	h * 0.54),
		(w * 0.45,	h * 0.45),
		(w * 0.28,	h * 0.45)
	]
	pg.draw.polygon(sf, "black", stack2Points, 2)
	pg.draw.polygon(sf, color, stack2Points)
	pg.draw.circle(sf, color, (w * 0.60, h * 0.55), w * 0.09)
	gunPoints = [
		(w * 0.60,	h * 0.54),
		(w * 0.58,	h * 0.54),
		(w * 0.66,	h * 0.40),
		(w * 0.67,	h * 0.42)
	]
	pg.draw.polygon(sf, "black", gunPoints, 2)
	pg.draw.polygon(sf, color, gunPoints)
	bodyPoints = [
		(w * 0.30,	h * 0.70),
		(w * 0.27,	h * 0.65),
		(w * 0.26,	h * 0.60),
		(w * 0.25,	h * 0.52),
		(w * 0.75,	h * 0.52),
		(w * 0.72,	h * 0.60),
		(w * 0.68,	h * 0.65),
		(w * 0.62,	h * 0.70),
	]
	pg.draw.polygon(sf, "black", bodyPoints, 2)
	pg.draw.polygon(sf, color, bodyPoints)
	return sf

def drawSubmarine(w, h, color) -> pg.Surface:
	sf = pg.Surface((w, h), pg.SRCALPHA)
	propellerPoints = [
		(w * 0.22,	h * 0.65),
		(w * 0.22,	h * 0.35),
		(w * 0.28,	h * 0.35),
		(w * 0.28,	h * 0.65)
	]
	pg.draw.polygon(sf, "black", propellerPoints, 2)
	pg.draw.polygon(sf, color, propellerPoints)
	bodyPoints = [
		(w * 0.39,	h * 0.62),
		(w * 0.25,	h * 0.55),
		(w * 0.25,	h * 0.45),
		(w * 0.39,	h * 0.38),
		(w * 0.70,	h * 0.38),
		(w * 0.80,	h * 0.44),
		(w * 0.83,	h * 0.50),
		(w * 0.80,	h * 0.56),
		(w * 0.70,	h * 0.62)
	]
	pg.draw.polygon(sf, "black", bodyPoints, 2)
	pg.draw.polygon(sf, color, bodyPoints)
	return sf
