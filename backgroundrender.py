import pygame as pg
import board as b
import math
import random
from hexutils import hexGeomertry, calculateHexPosition, calculateBoardDimensions, getAdjacentHexPositions
from datatypes import Coord, PlayerColors
from animationconstants import EXPLOSION_MARK_TIME

class GBackground():
	class ENode():
		def __init__(self, points):
			self.points = points
			self.timer = 0
			self.next = None

	def __init__(self, clock, board, hexW, hexH):
		self.clock = clock
		self.board = board
		boardWidth, boardHeight = calculateBoardDimensions(board.cols, board.rows, hexW, hexH)
		self.boardMask = getBoardOutlineMask(board, hexW, hexH, boardWidth, boardHeight)

		bgSf = pg.Surface((boardWidth, boardHeight), pg.SRCALPHA)
		fgSf = pg.Surface((boardWidth, boardHeight), pg.SRCALPHA)
		bgSf, fgSf = addFieldsToSurface((bgSf, fgSf), hexW, hexH, boardWidth, boardHeight)
		bgSf, fgSf = addTownsToSurface((bgSf, fgSf), hexW, hexH, board)
		self.bgSf = bgSf
		self.fgSf = fgSf

		self.hexW = hexW
		self.hexH = hexH
		self.boardWidth = boardWidth
		self.boardHeight = boardHeight

		self.explosionTimer = 0
		self.explosionPosition = (random.randint(0, int(self.boardWidth)), random.randint(0, int(self.boardHeight)))
		self.explotionPoints = getExplosionPoints(self.explosionPosition, self.hexW, self.hexH)

		self.explosionLLHead = self.ENode([])

	def draw(self, screen):
		finalSf = pg.Surface((self.boardWidth, self.boardHeight), pg.SRCALPHA)
		finalSf.blit(self.bgSf, (0, 0))

		cutoutForeground = pg.Surface((self.boardWidth, self.boardHeight), pg.SRCALPHA)
		cutoutForeground.blit(self.fgSf, (0, 0))

		last = self.explosionLLHead
		explosionLLCur = self.explosionLLHead.next
		while explosionLLCur is not None:
			explosionLLCur.timer += self.clock.get_time()
			if explosionLLCur.timer > EXPLOSION_MARK_TIME:
				last.next = None
				explosionLLCur = None
			else:
				explosionMask = self.getExplosionSurface(explosionLLCur.timer, explosionLLCur.points)
				cutoutForeground.blit(explosionMask, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
				last = explosionLLCur
				explosionLLCur = explosionLLCur.next

		finalSf.blit(cutoutForeground, (0, 0))

		screen.blit(finalSf, (0, 0))
		screen.blit(self.boardMask, (0, 0), special_flags=pg.BLEND_RGBA_MIN)

	def addExplosion(self, coord):
		center = calculateHexPosition(coord.col, coord.row, self.hexW, self.hexH)[1]
		newENode = self.ENode(getExplosionPoints(center, self.hexW, self.hexH))
		newENode.next = self.explosionLLHead.next
		self.explosionLLHead.next = newENode

	def getExplosionSurface(self, timer, points) -> pg.Surface:
		progress = timer / EXPLOSION_MARK_TIME
		sf = pg.Surface((self.boardWidth, self.boardHeight), pg.SRCALPHA)
		sf.fill((255, 255, 255, 255))
		cutoutColor = pg.Color(0, 0, 0, 0).lerp((255, 255, 255, 255), progress)
		pg.draw.polygon(sf, cutoutColor, points)
		return sf

def getExplosionPoints(center, hexW, hexH) -> list[(float, float)]:
	points = []
	outerMaxRadius = hexW * 1.5
	outerMinRadius = hexW * 0.8
	innerMaxRadius = hexW * 0.8
	innerMinRadius = hexW * 0.4
	startAngle = 0
	curAngle = startAngle
	isIn = True
	while curAngle < (math.pi * 2):
		radius = 0
		if isIn:
			radius = random.random() * (innerMaxRadius - innerMinRadius) + innerMinRadius
		else:
			radius = random.random() * (outerMaxRadius - outerMinRadius) + outerMinRadius
		x = center[0] + radius * math.cos(curAngle)
		y = center[1] + radius * math.sin(curAngle)
		points.append((x, y))
		newAngle = random.random() * (math.pi * 0.1) + math.pi * 0.01
		curAngle += newAngle
		isIn = not isIn
	return points

def addTownToSurface(sfs, hexW, hexH, center, geometry, size, specialColor = None) -> (pg.Surface, pg.Surface):
	"""
	Draw random brown circles starting from the center and then spreading out
	"""
	bgSf, fgSf = sfs
	blotW = hexW / 10
	blotH = hexH / 10

	colorJitter1 = random.randint(0, 60) - 30
	colorJitter2 = random.randint(0, 60) - 30
	colorJitter3 = random.randint(0, 60) - 30

	colors = [
		(212 + colorJitter1, 137 + colorJitter1, 61),
		(133 + colorJitter2, 68 + colorJitter2, 3),
		(105 + colorJitter3, 53 + colorJitter3, 2),
		(84, 126, 42),
	]
	colorWeights = [ 1 for _ in colors ]
	if specialColor is not None:
		colors.append(pg.Color(specialColor).lerp((100, 100, 100), 0.3))
		colorWeights.append(0.4)
	deadColors = [
		(40, 40, 40),
		(20, 20, 20),
		(70, 70, 70),
	]

	minDepth = 6
	continueBarBase = 0.75
	jumpBarBase = 0.8
	if size == 1:
		minDepth = 4
		continueBarBase = 0.7
		jumpBarBase = 0.75
	elif size == 3:
		minDepth = 8
		continueBarBase = 0.85
		jumpBarBase = 0.90

	seen = set()
	posQueue = [ (center, 0) ]
	while posQueue:
		curPos, depth = posQueue.pop()
		if curPos in seen:
			continue
		seen.add(curPos)

		color = random.choices(colors, weights=colorWeights, k=1)[0]
		pg.draw.circle(fgSf, color, curPos, blotW / 2)
		pg.draw.circle(bgSf, random.choice(deadColors), curPos, blotW / 2)

		continueBar = continueBarBase ** (depth * 2)
		jumpBar = jumpBarBase ** (depth * 2)
		if depth < minDepth or random.random() < continueBar:
			nextPoses = getAdjacentHexPositions(curPos, blotW, blotH)
			for p in nextPoses:
				posQueue.append((p, depth + 1))
		elif random.random() < jumpBar:
			nextPoses = getAdjacentHexPositions(curPos, blotW * 2, blotH * 2)
			for p in nextPoses:
				if random.random() < 0.5:
					posQueue.append((p, depth + 2))

	return (bgSf, fgSf)

def addTownsToSurface(sfs, hexW, hexH, board) -> (pg.Surface, pg.Surface):
	posToSpace = { calculateHexPosition(s.coord.col, s.coord.row, hexW, hexH)[1]: s for s in b.getAllSpaces(board) if s.isTown or s.isCapital or s.isPort }
	geo = hexGeomertry(hexW, hexH)
	for centerPos, space in posToSpace.items():
		size = (
			1 if space.isPort else
			2 if space.isTown else
			3 if space.isCapital else
			0
		)
		specialColor = (
			PlayerColors[space.ownedBy] if space.isCapital else
			None
		)
		sfs = addTownToSurface(sfs, hexW, hexH, centerPos, geo, size, specialColor)
	return sfs

	
def addFieldsToSurface(sfs, hexW, hexH, boardWidth, boardHeight) -> (pg.Surface, pg.Surface):
	bgSf, fgSf = sfs
	relatives = [
		10,
		9,
		8,
		6
	]
	scales = [r * 14 for r in relatives]
	greens = [(r * 1, r * 1.5, r * 0.5) for r in scales]
	reds = [(r * 1.2, r * 0.6, r * 0.3) for r in scales]
	fgSf.fill(greens[1])
	bgSf.fill(reds[1])
	for i in range(1000):
		colorIdx = random.randint(0, len(greens) - 1)
		points = getRandomRectPoints(boardWidth, boardHeight, (hexW * 0.1, hexW * 0.6))
		pg.draw.polygon(fgSf, greens[colorIdx], points)
		pg.draw.polygon(bgSf, reds[colorIdx], points)
		if (points[0] - points[2]).length() > hexW * 0.4 and colorIdx < 2 and random.random() > 0.3:
			lines = random.randint(0, 3)
			for i in range(lines):
				progress = (i + 1) / (lines + 1)
				lineStart = points[0].lerp(points[3], progress)
				lineEnd = points[1].lerp(points[2], progress)
				size = random.randint(5, 10)
				colorIdx = random.randint(0, len(greens) - 1)
				pg.draw.line(fgSf, greens[colorIdx], lineStart, lineEnd, size)
				pg.draw.line(bgSf, reds[colorIdx], lineStart, lineEnd, size)
	return (bgSf, fgSf)

def getRandomRectPoints(maxX, maxY, sizeRange) -> list[(float, float)]:
	minSize, maxSize = sizeRange
	width = random.random() * (maxSize - minSize) + minSize
	height = random.random() * (maxSize - minSize) + minSize
	startAngle = random.random() * 360
	startV = pg.Vector2(random.random() * maxX, random.random() * maxY)

	twoV = pg.Vector2(0, 1).rotate(startAngle)
	twoV.scale_to_length(width)
	twoV = startV + twoV
	threeV = pg.Vector2(0, 1).rotate(startAngle + 90 + random.uniform(-10, 10))
	threeV.scale_to_length(height)
	threeV = twoV + threeV
	fourV = pg.Vector2(0, 1).rotate(startAngle + 180 + random.uniform(-10, 10))
	fourV.scale_to_length(width)
	fourV = threeV + fourV

	return (startV, twoV, threeV, fourV)


def getBoardOutlineMask(board, hexW, hexH, boardWidth, boardHeight) -> pg.Surface:
	"""
	Return surface map that is the entire board
	"""
	geometry = hexGeomertry(hexW, hexH)
	rows = board.rows
	cols = board.cols

	topEdgePoints = []
	for c in range(cols):
		r = 0
		tlPoint = geometry.points[4]
		trPoint = geometry.points[3]
		pos = calculateHexPosition(c, r, hexW, hexH)[0]
		point1 = (tlPoint[0] + pos[0], tlPoint[1] + pos[1])
		point2 = (trPoint[0] + pos[0], trPoint[1] + pos[1])
		topEdgePoints.append(point1)
		topEdgePoints.append(point2)

	rightEdgePoints = []
	for r in range(rows):
		c = cols - 1
		rPoint = geometry.points[2]
		brPoint = geometry.points[1]
		pos = calculateHexPosition(c, r, hexW, hexH)[0]
		point1 = (rPoint[0] + pos[0], rPoint[1] + pos[1])
		point2 = (brPoint[0] + pos[0], brPoint[1] + pos[1])
		rightEdgePoints.append(point1)
		rightEdgePoints.append(point2)

	bottomEdgePoints = []
	for c in reversed(range(cols)):
		r = rows - 1
		brPoint = geometry.points[1]
		blPoint = geometry.points[0]
		pos = calculateHexPosition(c, r, hexW, hexH)[0]
		point1 = (brPoint[0] + pos[0], brPoint[1] + pos[1])
		point2 = (blPoint[0] + pos[0], blPoint[1] + pos[1])
		bottomEdgePoints.append(point1)
		bottomEdgePoints.append(point2)

	leftEdgePoints = []
	for r in reversed(range(rows)):
		c = 0
		lPoint = geometry.points[5]
		tlPoint = geometry.points[4]
		pos = calculateHexPosition(c, r, hexW, hexH)[0]
		point1 = (lPoint[0] + pos[0], lPoint[1] + pos[1])
		point2 = (tlPoint[0] + pos[0], tlPoint[1] + pos[1])
		leftEdgePoints.append(point1)
		leftEdgePoints.append(point2)

	allPoints = topEdgePoints + rightEdgePoints + bottomEdgePoints + leftEdgePoints

	sf = pg.Surface((boardWidth, boardHeight + 1), pg.SRCALPHA)
	pg.draw.polygon(sf, (255, 255, 255, 255), allPoints)

	return sf