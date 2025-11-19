import pygame as pg
import math
import random
from hexutils import calculateHexPosition, hexGeomertry
from datatypes import PlayerColors
from renders.animationconstants import BORDER_FADE_IN_TIME, BORDER_FADE_OUT_TIME

class GSpace:
	def __init__(self, clock, GAME_FONT, space, c, r, w, h):
		self.clock = clock
		self.GAME_FONT = GAME_FONT
		self.space = space
		pos, center = calculateHexPosition(c, r, w, h)
		self.pos = pos
		self.center = center
		geometry = hexGeomertry(w, h)
		self.geometry = geometry
		self.points = [(p[0] + pos[0], p[1] + pos[1]) for p in geometry.points]
		self.w = w
		self.h = h
		self.highlight = False
		self.oldBorders = [None, None, None, None, None, None]
		self.borderClocks = [-1, -1, -1, -1, -1, -1]

		self.borderSurface = self.getRefreshedBorderSurface(space)

		self.coastMask, self.beachMask = getCoastMask(w, h, space.borderIsWater)

	def refreshSpace(self, newSpace):
		oldBorders = self.space.borderColors
		newBorders = newSpace.borderColors
		for idx, color in enumerate(newBorders):
			if oldBorders[idx] != color:
				self.oldBorders[idx] = oldBorders[idx]
				self.borderClocks[idx] = 0
		self.space = newSpace

	# Test if dot is within concave shape described by points
	def collidePoint(self, dot) -> bool:
		if dot is None:
			return False
		for pi in range(len(self.points)):
			ps = self.points[pi]
			pe = self.points[(pi + 1) % len(self.points)]
			vl = pg.Vector2(ps) - pg.Vector2(pe)
			vd = pg.Vector2(ps) - pg.Vector2(dot)
			inbounds = vl.cross(vd) < 0
			if not inbounds:
				return False
		return True

	def getRefreshedBorderSurface(self, space) -> pg.Surface:
		mappedColors = [None if c is None else pg.Color(c) for c in space.borderColors]
		mappedOldColors = [None if c is None else pg.Color(c) for c in self.oldBorders]
		return getBorderSf(self.geometry, mappedColors, mappedOldColors, self.borderClocks, BORDER_FADE_IN_TIME, BORDER_FADE_OUT_TIME, False)

	def changeHighlight(self, isHighlighted):
		self.highlight = isHighlighted

	def draw(self, screen, isHovered):
		space = self.space
		mainSf = pg.Surface((self.w, self.h), pg.SRCALPHA)
		# mainSf.fill((255 * self.space.coord.col / 12, 255 * self.space.coord.row / 8, 0))

		shouldUpdateBorderSf = False
		for i, bc in enumerate(self.borderClocks):
			newTime = bc
			if bc != -1:
				shouldUpdateBorderSf = True
				newTime += self.clock.get_time()
			if bc >= max(BORDER_FADE_IN_TIME, BORDER_FADE_OUT_TIME):
				self.borderClocks[i] = -1
				self.oldBorders[i] = self.space.borderColors[i]
			else:
				self.borderClocks[i] = newTime
		if shouldUpdateBorderSf:
			self.borderSurface = self.getRefreshedBorderSurface(space)

		fgcolor = (
			(255, 255, 0, 200) if self.highlight else # TODO: Don't clip the highlight by the coast
			(0, 0, 0, 0) if not space.isWater else
			# "darkolivegreen3" if space.isCoastal or space.isInland else
			"blue3" if space.isWater else
			"purple"
		)
		pg.draw.polygon(mainSf, fgcolor, self.geometry.points)

		beachSurface = pg.Surface((self.w, self.h), pg.SRCALPHA)
		beachSurface.fill((230, 230, 20, 255))
		beachSurface.blit(self.beachMask, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
		mainSf.blit(beachSurface, (0, 0))

		# mappedColors = [None if c is None else pg.Color(c) for c in space.borderColors]
		# mappedOldColors = [None if c is None else pg.Color(c) for c in self.oldBorders]
		# borderSurface = drawBorder(self.geometry, mappedColors, mappedOldColors, self.borderClocks, BORDER_FADE_IN_TIME, BORDER_FADE_OUT_TIME, False)
		mainSf.blit(self.borderSurface, (0, 0))

		waterSurface = pg.Surface((self.w, self.h), pg.SRCALPHA)
		waterSurface.fill("blue3")
		waterSurface.blit(self.coastMask, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
		mainSf.blit(waterSurface, (0, 0))

		if space.isTown:
			sf = drawTown(self.w, self.h, "burlywood4")
			mainSf.blit(sf,  (0, 0))
		if space.isCapital:
			innerColor = PlayerColors[space.firstOwner] if space.firstOwner != space.ownedBy else None
			sf = drawCapital(self.w, self.h, PlayerColors[space.ownedBy], innerColor)
			mainSf.blit(sf,  (0, 0))
		if space.isPort:
			sf = drawPort(self.w, self.h, "chocolate3")
			mainSf.blit(sf,  (0, 0))

		screen.blit(mainSf, self.pos)

		pg.draw.polygon(screen, "#555555", self.points, 1)
		if isHovered:
			sf = drawHoverColor(self.w, self.h, self.geometry.points)
			screen.blit(sf, self.pos)

		# for idx, p in enumerate(self.debug):
		# 	color = "red" if idx % 2 == 0 else "blue"
		# 	size = 5 if idx % 2 == 0 else 8
		# 	pg.draw.circle(screen, color, pg.Vector2(self.pos) + p, size)

		# if coordToDraw is not None and coordToDraw in self.space.pointToMoves:
		# 	moves = self.space.pointToMoves[coordToDraw]
		# 	sf = drawDebugString(self.w, self.h, self.GAME_FONT, f"{moves}")
		# 	screen.blit(sf, self.pos)

def getCoastPoint(leftIsWater, rightIsWater, innerPoint, outerPoint, angle):
	"""
	if lastWater & thisWater: start = smallPoints
	if ! lastWater & ! thisWater: start = fullPoints
	else: start = midPoint
	"""
	if leftIsWater and rightIsWater:
		return innerPoint
	elif not leftIsWater and not rightIsWater:
		return outerPoint
	else:
		difference = pg.Vector2(outerPoint) - pg.Vector2(innerPoint)
		rotationAngle = angle if leftIsWater else -angle
		rotated = difference.rotate(rotationAngle)
		newPoint = pg.Vector2(innerPoint) + rotated
		return newPoint

def cerp(start, end, progress) -> float:
	"""
	Cosine interpolation between start and end point
	progress: float between 0 and 1
	"""
	g = lambda a: (1 - math.cos(math.pi * a)) / 2
	newPoint = (1 - g(progress)) * start + g(progress) * end
	return newPoint

def getCoastMask(w, h, borderIsWater) -> (pg.Surface, pg.Surface):
	"""
	go from point to point of hexagon .9 as large
	each side should end exactly at point
	each pixel step can go in or out with random prob proportional to distance from mid line

	1st return: Surface where the outside water edge is full white and rest is transparent
	2nd return: surface where beach edge is full white and rest is transparent
	"""
	smallScale = 0.75
	smallGeo = hexGeomertry(w * smallScale, h * smallScale)
	smallPoints = [(p[0] + (1 - smallScale) * w / 2, p[1] + (1 - smallScale) * h / 2) for p in smallGeo.points]
	midScale = 0.9
	midGeo = hexGeomertry(w * midScale, h * midScale)
	midPoints = [(p[0] + (1 - midScale) * w / 2, p[1] + (1 - midScale) * h / 2) for p in midGeo.points]
	fullGeo = hexGeomertry(w, h)
	fullPoints = fullGeo.points

	outerSf = pg.Surface((w, h), pg.SRCALPHA)
	innerSf = pg.Surface((w, h), pg.SRCALPHA)

	allOuterPoints = []
	allInnerPoints = []
	for pointIdx in range(6):
		thisWater = borderIsWater[(4 - pointIdx) % 6]
		lastWater = borderIsWater[(4 - pointIdx + 1) % 6]
		nextWater = borderIsWater[(4 - pointIdx - 1) % 6]

		startPoint = getCoastPoint(lastWater, thisWater, midPoints[pointIdx], fullPoints[pointIdx], fullGeo.angles[pointIdx])
		endPoint = getCoastPoint(thisWater, nextWater, midPoints[(pointIdx + 1) % 6], fullPoints[(pointIdx + 1) % 6], fullGeo.angles[(pointIdx + 1) % 6])

		innerStartPoint = getCoastPoint(lastWater, thisWater, smallPoints[pointIdx], fullPoints[pointIdx], fullGeo.angles[pointIdx])
		innerEndPoint = getCoastPoint(thisWater, nextWater, smallPoints[(pointIdx + 1) % 6], fullPoints[(pointIdx + 1) % 6], fullGeo.angles[(pointIdx + 1) % 6])

		outerMiddlePoints = []
		innerMiddlePoints = []
		if thisWater:
			# Generate 4 random points
			# seeds = [0, r1, r2, r3, r4, 0]
			# Assuming starting and ending at 0, interpolate 3 points between each random point using cosine interpolation
			# randCurvPoints = [0, i011, i012, i013, r1, i121, i122, i123, r2, ...]
			numRand = 4
			inters = 10
			randoms = [ min(max(random.gauss(0, 0.5), -1), 1) for _ in range(numRand) ]
			seeds = [0] + randoms + [0]
			randCurvPoints = [0]
			for i in range(1, (numRand + 1) * (inters + 1)):
				start = seeds[int(i / (inters + 1))]
				end = seeds[int(i / (inters + 1)) + 1]
				progress = (i % (inters + 1)) / (inters + 1) # (0, 1)
				thisPoint = cerp(start, end, progress)
				randCurvPoints.append(thisPoint)

			# Add octave values to each point where:
			# newpoint = pointlist[i] + dampingFactor^octave * pointlist[i * 2^octave % len]
			dampingFactor = 0.4
			fbmRandCurvPoints = []
			for idx, point in enumerate(randCurvPoints):
				runningVal = 0
				for octave in range(4):
					octaveVal = dampingFactor ** octave * randCurvPoints[(idx * 1 << octave) % len(randCurvPoints)]
					runningVal += octaveVal
				fbmRandCurvPoints.append(runningVal)

			# Draw lines between each point
			amplitude = (fullGeo.height - midGeo.height) / 2
			dx = (endPoint[0] - startPoint[0]) / len(fbmRandCurvPoints)
			dy = (endPoint[1] - startPoint[1]) / len(fbmRandCurvPoints)
			angle = math.atan2(dy, dx)

			indx = (innerEndPoint[0] - innerStartPoint[0]) / len(fbmRandCurvPoints)
			indy = (innerEndPoint[1] - innerStartPoint[1]) / len(fbmRandCurvPoints)
			inAngle = math.atan2(indy, indx)

			for i, randValue in enumerate(fbmRandCurvPoints):
				gain = pg.Vector2(dx * (i + 1), dy * (i + 1))

				noise_offset = randValue * amplitude
				randomOffset = pg.Vector2(noise_offset * math.sin(angle), -noise_offset * math.cos(angle))

				nextPoint = startPoint + gain + randomOffset
				outerMiddlePoints.append(nextPoint)

				innerGain = pg.Vector2(indx * (i + 1), indy * (i + 1))
				nextInnerPoint = innerStartPoint + innerGain + randomOffset
				innerMiddlePoints.append(nextInnerPoint)
			# TODO: Maybe smooth innerMiddlePoints

		thisEdgePoints = [startPoint] + outerMiddlePoints + [endPoint]
		allOuterPoints += thisEdgePoints
		thisInnerEdgePoints = [innerStartPoint] + innerMiddlePoints + [innerEndPoint]
		allInnerPoints += thisInnerEdgePoints

	pg.draw.polygon(outerSf, (255, 255, 255, 255), fullPoints)
	pg.draw.polygon(outerSf, (0, 0, 0, 0), allOuterPoints)
	pg.draw.polygon(innerSf, (255, 255, 255, 255), allOuterPoints)
	pg.draw.polygon(innerSf, (0, 0, 0, 0), allInnerPoints)
	return outerSf, innerSf



def drawDebugString(w, h, font, text):
	sf = pg.Surface((w, h), pg.SRCALPHA)
	textColor = (0, 0, 0, 150)
	text_surface, text_rect = font.render(text, fgcolor=textColor, size=int(w * .23))
	txp = (w - text_rect.width) / 2
	typ = (h - text_rect.height) / 2
	sf.blit(text_surface, (txp, typ))
	return sf

def drawHoverColor(w, h, points):
	sf = pg.Surface((w, h), pg.SRCALPHA)
	color = (255, 255, 255, 50)
	pg.draw.polygon(sf, color, points)
	return sf


# geometry: Geometry
# colors: [pg.Color, pg.Color, pg.Color, pg.Color, pg.Color, pg.Color]
#  If pg.Color is None then don't draw
#  colors starts on bottom side and then goes cw
# oldSideColors: [pg.Color, pg.Color, pg.Color, pg.Color, pg.Color, pg.Color]
def getBorderSf(geometry, sideColors, oldSideColors, sideClocks, sideFadeInTime, sideFadeOutTime, isInnerAngle) -> pg.Surface:
	# TODO: Could save computation by only redrawing the border surface when it changes
	w = geometry.width
	h = geometry.height
	points = geometry.points
	runningAngles = geometry.runningAngles
	baseSurface = pg.Surface((w, h), pg.SRCALPHA)

	alphaMax = 150
	alphaMin = 0
	startFade = int(h * 0.1)
	endFade = int(h * 0.35)

	inAngleAdjust = 2 if isInnerAngle else 0
	center = (w / 2, h / 2)
	np = len(points)
	for pi, color in enumerate(sideColors):
		oldColor = oldSideColors[pi]
		colorToUse = color
		goReverse = False
		if color is None:
			if oldColor is None:
				continue
			else:
				colorToUse = oldColor
				goReverse = True

		borderSurface = pg.Surface((w, h), pg.SRCALPHA)

		leftV = pg.Vector2(points[pi])
		rightV = pg.Vector2(points[(pi + 1) % np])

		leftV = (leftV - center).rotate(runningAngles[pi]) + center
		rightV = (rightV - center).rotate(runningAngles[pi]) + center

		# Vector encoding difference between center->rotated side and center->og side		
		magicV = pg.Vector2(0, h - leftV[1])
		leftV = leftV + magicV
		rightV = rightV + magicV

		# Not center, instead oposing point for target vector
		leftTV = pg.Vector2(points[(pi - 1 - inAngleAdjust) % np])
		rightTV = pg.Vector2(points[(pi + 2 + inAngleAdjust) % np])
		leftTV = (leftTV - center).rotate(runningAngles[pi]) + center + magicV
		rightTV = (rightTV - center).rotate(runningAngles[pi]) + center + magicV

		leftNormV = (leftTV - leftV).normalize()
		rightNormV = (rightTV - rightV).normalize()

		stepl = rightNormV[1] / leftNormV[1]
		stepr = 1
		finishTime = sideFadeOutTime if goReverse else sideFadeInTime
		animationProgress = 1 if sideClocks[pi] == -1 else min(sideClocks[pi] / finishTime, 1)
		if goReverse:
			animationProgress = 1 - animationProgress
		numLinesToDraw = int(endFade * animationProgress)
		for i in range(numLinesToDraw):
			alpha = 255
			if i > startFade:
				deltaFade = endFade - startFade
				alpha = alphaMin + (alphaMax - alphaMin) * (deltaFade - (i - startFade + 1)) / deltaFade
			newLeftV = leftNormV * stepl * i + leftV
			newRightV = rightNormV * stepr * i + rightV

			c = (colorToUse.r, colorToUse.g, colorToUse.b, alpha)
			pg.draw.line(borderSurface, c, newLeftV, newRightV, 1)

		borderSurface = pg.transform.rotate(borderSurface, runningAngles[pi])
		rect = borderSurface.get_rect()
		newPos = (
			(w - rect[2]) / 2,
			(h - rect[3]) / 2
		) - magicV.rotate(-runningAngles[pi])
		baseSurface.blit(borderSurface, newPos)
	return baseSurface


def drawPort(w, h, color) -> pg.Surface:
	mainColor = (210, 105, 30)
	sf = pg.Surface((w, h), pg.SRCALPHA)
	points = [
		(w * 0.20,	h * 0.70),
		(w * 0.20,	h * 0.60),
		(w * 0.80,	h * 0.60),
		(w * 0.80,	h * 0.70),

		(w * 0.75,	h * 0.70),
		(w * 0.75,	h * 0.90),
		(w * 0.67,	h * 0.90),
		(w * 0.67,	h * 0.70),

		(w * 0.54,	h * 0.70),
		(w * 0.54,	h * 0.90),
		(w * 0.46,	h * 0.90),
		(w * 0.46,	h * 0.70),

		(w * 0.33,	h * 0.70),
		(w * 0.33,	h * 0.90),
		(w * 0.25,	h * 0.90),
		(w * 0.25,	h * 0.70),
	]
	pg.draw.polygon(sf, mainColor, points)
	pg.draw.polygon(sf, "black", points, 2)
	points = [
		(w * 0.35,	h * 0.60),
		(w * 0.35,	h * 0.45),
		(w * 0.67,	h * 0.20),
		(w * 0.71,	h * 0.20),
		(w * 0.71,	h * 0.38),
		(w * 0.65,	h * 0.38),
		(w * 0.65,	h * 0.32),
		(w * 0.62,	h * 0.32),
		(w * 0.43,	h * 0.48),
		(w * 0.43,	h * 0.60),
	]
	pg.draw.polygon(sf, mainColor, points)
	pg.draw.polygon(sf, "black", points, 2)
	return sf

def drawTown(w, h, color) -> pg.Surface:
	# colorMain = (123, 63, 0)
	colorMain = (165, 135, 85)
	colorSecondary = (119, 95, 65)
	sf = pg.Surface((w, h), pg.SRCALPHA)
	points = [
		(w * 0.2,	h * 0.8),
		(w * 0.2,	h * 0.5),
		(w * 0.37,	h * 0.3),
		(w * 0.54,	h * 0.5),
		(w * 0.54,	h * 0.8)
	]
	pg.draw.polygon(sf, colorMain, points)
	pg.draw.polygon(sf, "black", points, 2)
	doorPoints = [
		(w * 0.34,	h * 0.80),
		(w * 0.34,	h * 0.69),
		(w * 0.40,	h * 0.69),
		(w * 0.40,	h * 0.80)
	]
	pg.draw.polygon(sf, colorSecondary, doorPoints)
	pg.draw.polygon(sf, "black", doorPoints, 2)
	windowPoints = [
		(w * 0.25,	h * 0.68),
		(w * 0.25,	h * 0.61),
		(w * 0.30,	h * 0.61),
		(w * 0.30,	h * 0.68)
	]
	pg.draw.polygon(sf, colorSecondary, windowPoints)
	pg.draw.polygon(sf, "black", windowPoints, 2)
	points = [
		(w * 0.4,	h * 0.82),
		(w * 0.4,	h * 0.55),
		(w * 0.57,	h * 0.2),
		(w * 0.74,	h * 0.55),
		(w * 0.74,	h * 0.82)
	]
	pg.draw.polygon(sf, colorMain, points)
	pg.draw.polygon(sf, "black", points, 2)
	doorPoints = [
		(w * 0.53,	h * 0.82),
		(w * 0.53,	h * 0.68),
		(w * 0.61,	h * 0.68),
		(w * 0.61,	h * 0.82)
	]
	pg.draw.polygon(sf, colorSecondary, doorPoints)
	pg.draw.polygon(sf, "black", doorPoints, 2)
	windowPoint = (w * 0.58,	h * 0.5)
	pg.draw.circle(sf, colorSecondary, windowPoint, w * 0.07)
	pg.draw.circle(sf, "black", windowPoint, w * 0.07, 2)
	return sf

def drawCapital(w, h, color, innerColor = None) -> pg.Surface:
	sf = pg.Surface((w, h), pg.SRCALPHA)
	def makeStar(outerRadius, c):
		points = []
		innterRadius = outerRadius * 0.4
		for n in range(5):
			outerAngle = -math.pi / 2 + math.pi / 5 * (n * 2)
			innerAngle = -math.pi / 2 + math.pi / 5 * (n * 2 + 1)
			outX = w / 2 + outerRadius * math.cos(outerAngle)
			outY = h / 2 + outerRadius * math.sin(outerAngle)
			inX = w / 2 + innterRadius * math.cos(innerAngle)
			inY = h / 2 + innterRadius * math.sin(innerAngle)
			points.append((outX, outY))
			points.append((inX, inY))
		pg.draw.polygon(sf, pg.Color(c).lerp((255, 255, 255), 0.5), points)

	defaultRadius = (w + h) / 4
	makeStar(defaultRadius, color)
	if innerColor is not None:
		makeStar(defaultRadius * 0.5, innerColor)
	return sf