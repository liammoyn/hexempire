import math
from datatypes import Geometry

def calculateBoardDimensions(cols, rows, w, h) -> (float, float):
	# TODO: Hardcoded to points
	boardHeight = rows * h + h / 2
	boardWidth = cols * w * 0.75 + w / 4
	return (boardWidth, boardHeight)

def calculateHexPosition(c, r, w, h):
	oddOffset = h / 2 if c % 2 == 1 else 0
	xp = c * w * 0.75
	yp = r * h + oddOffset
	pos = (xp, yp)
	center = (xp + w / 2, yp + h / 2)
	return pos, center

def getAdjacentHexPositions(pos, w, h) -> list[(float, float)]:
	# bottom left, ccw
	offsets = [
		(w * -0.75, h * 0.5),
		(w * 0, 	h * 1),
		(w * 0.75, 	h * 0.5),
		(w * 0.75, 	h * -0.5),
		(w * 0, 	h * -1),
		(w * 0.25, 	h * -0.5)
	]
	return [ (pos[0] + offset[0], pos[1] + offset[1]) for offset in offsets ]

def hexGeomertry(w, h) -> Geometry:
	# bottom left, ccw
	points = [
		(w * 0.25, 	h * 1),
		(w * 0.75, 	h * 1),
		(w * 1, 	h * 0.5),
		(w * 0.75, 	h * 0),
		(w * 0.25, 	h * 0),
		(w * 0, 	h * 0.5)
	]

	# top, cw
	slopes = []
	for i in range(len(points)):
		startP = points[i]
		endP = points[(i + 1) % len(points)]
		slope = (endP[1] - startP[1]) / (endP[0] - startP[0])
		slopes.append(slope)

	# top left, cw
	tans = []
	for i in range(len(slopes)):
		startSlope = slopes[(i - 1) % len(slopes)]
		endSlope = slopes[i]
		tan = (endSlope - startSlope) / (1 + startSlope * endSlope)
		tans.append(tan)

	angles = list(map(lambda t: math.atan(t) * (180 / math.pi), tans))

	runningAngles = [0]
	for i in range(len(angles)):
		a = -angles[(i + 1) % len(angles)]
		runningAngles.append(a + runningAngles[i])

	return Geometry(w, h, points, angles, runningAngles)
