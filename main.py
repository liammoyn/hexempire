import os
import pygame as pg
import pygame.freetype
import math
import queue
import threading
from renders.inputrender import GInputBox
from renders.statusrender import GStatus
from gamecontroller import GameStateController
from players.naive_player import NaivePlayer
from players.evaluation_player import EvaluationPlayer
from players.objective_player import ObjectivePlayer
from players.computer_wrapper import ComputerWrapper, COMPUTER_MOVE_TYPE, COMPUTER_EVALS_TYPE
from hexutils import calculateBoardDimensions

import cProfile

def tryfloat(s) -> float or None:
	try:
		f = float(s)
		return f
	except ValueError:
		return None

class MainRender:
	def __init__(self, GAME_FONT, cols, rows):
		self.GAME_FONT = GAME_FONT
		self.cols = cols
		self.rows = rows

		boarderWidth = 20
		boarderHeight = 50
		dwidth = 1280							#display_width
		dheight = int((1080 / 1920) * dwidth) 	#display_height
		vwidth = dwidth - 2 * boarderWidth 		#viewport_width
		vheight = dheight - 2 * boarderHeight 	#viewport_height

		# vs = vertical spacing = distance from center to top
		# hs = horizontal spacing = distance from center to point
		vs = vheight / (2 * rows + 1)
		hs = (vs * 2 / math.sqrt(3))
		hexW = int(hs * 2)
		hexH = int(vs * 2)

		boardWidth, boardHeight = calculateBoardDimensions(cols, rows, hexW, hexH)
		h_offset = (vwidth - boardWidth) / 2

		self.screen = pg.display.set_mode((dwidth, dheight))
		self.vp = pg.Surface((boardWidth, boardHeight + 1), pg.SRCALPHA)

		viewX = boarderWidth + h_offset
		viewY = boarderHeight
		self.vpPos = pg.Vector2(viewX, viewY)
		self.vpRect = pg.Rect(viewX, viewY, boardWidth, boardHeight)

		# TODO: Make input and status box dynamic based on display properties

		water_level_ib = GInputBox(GAME_FONT, 100, 9, 100, 32)
		port_level_ib = GInputBox(GAME_FONT, 220, 9, 100, 32)
		town_level_ib = GInputBox(GAME_FONT, 340, 9, 100, 32)
		self.input_boxes = [water_level_ib, port_level_ib, town_level_ib]

		self.status_box = GStatus(GAME_FONT, 500, 5, 300, 40)
		# TODO: Add a button for ending turn early

		print(f"{dwidth} {dheight} {hexW} {hexH}")

		computerPlayers = [
			ComputerWrapper(ObjectivePlayer(0), 0),
			ComputerWrapper(ObjectivePlayer(1), 1),
			ComputerWrapper(ObjectivePlayer(2), 2),
			ComputerWrapper(ObjectivePlayer(3), 3)
		]
		isUserPlayer = [False, False, False, False]
		self.computerQueues = []
		self.computerThreads = []
		for computerPlayer in computerPlayers:
			computerQueue = queue.Queue()
			ct = threading.Thread(target=computerPlayer.startGameThinking, args=(computerQueue,))
			ct.daemon = True
			self.computerQueues.append(computerQueue)
			self.computerThreads.append(ct)

		self.clock = pg.time.Clock()
		startStepping = True
		self.gamecontroller = GameStateController(GAME_FONT, self.clock, cols, rows, hexW, hexH, isUserPlayer, startStepping)
		self.running = False
		self.savedGameState = None
		self.gameStatusHistory = [ self.gamecontroller.getGameStateString() ]
		self.isNewGame = True

		# self.zoom = 1
		# self.scroll = 0


	def start_mainloop(self):
		for computerThread in self.computerThreads:
			computerThread.start()
		lastMoveCounter = None
		self.gamecontroller.startGame()

		avgFps = 0
		fpss = 0

		timeRunning = 0
		self.running = True
		while self.running:# and timeRunning < 10_000:
			self.clock.tick()
			# timeRunning += self.clock.get_time()
			# fps = 1000 / self.clock.get_time()
			# fpss += 1
			# avgFps = avgFps * (fpss - 1) / fpss + fps / fpss
			
			self.handleEvents(pg.event.get())

			gameStatus = self.gamecontroller.getStatus()

			if gameStatus.moveCounter != lastMoveCounter or self.isNewGame:
				self.isNewGame = False
				for queue in self.computerQueues:
					queue.put(gameStatus)
				lastMoveCounter = gameStatus.moveCounter

			self.draw(gameStatus)

			pg.display.flip()
		print(avgFps)


	def handleEvents(self, eventList):
		for event in eventList:
			if event.type == pg.QUIT:
				print(self.savedGameState)
				self.running = False
			for box in self.input_boxes:
				box.handle_event(event)
			if event.type == pg.KEYDOWN:
				if event.key == pg.K_SPACE:
					waterFloat, portFloat, townFloat = self.getNewBoardValues()
					self.gamecontroller.newGame(waterFloat, portFloat, townFloat)
					self.gameStatusHistory = [ self.gamecontroller.getGameStateString() ]
					self.isNewGame = True
				elif event.key == pg.K_e:
					self.gamecontroller.handleUserEndTurn()
				elif event.key == pg.K_RIGHT:
					self.gameStatusHistory.append(self.gamecontroller.getGameStateString())
					self.gamecontroller.handleStepForward()
				elif event.key == pg.K_LEFT and len(self.gameStatusHistory) > 1:
					lastGameState = self.gameStatusHistory.pop()
					self.gamecontroller.useGameStateString(lastGameState)
				elif event.key == pg.K_s:
					self.gamecontroller.toggleStepping()
				elif event.key == pg.K_p:
					self.savedGameState = self.gamecontroller.getGameStateString()
				elif event.key == pg.K_l and self.savedGameState is not None:
					self.gamecontroller.useGameStateString(self.savedGameState)
				elif event.key == pg.K_z:
					self.zoom = self.zoom * 0.9
				elif event.key == pg.K_x:
					self.zoom = self.zoom * 1.1
				elif event.key == pg.K_q:
					self.scroll -= 25
				elif event.key == pg.K_w:
					self.scroll += 25
			elif event.type == pg.MOUSEBUTTONUP:
				if self.vpRect.collidepoint(event.pos):
					self.gamecontroller.handleUserClick(event.pos - self.vpPos)
			elif event.type == COMPUTER_MOVE_TYPE:
				# Computer players will publish moves to pg.event.post() when they have them
				self.gamecontroller.handleComputerMove(event.move, event.playerId)
			elif event.type == COMPUTER_EVALS_TYPE:
				# Computer players will publish moves to pg.event.post() when they have them
				self.gamecontroller.handleComputerEvals(event.moveEvaluations, event.objectiveEvaluations, event.playerId)


	def draw(self, gameStatus):
		self.screen.fill("white")
		self.vp.fill("white")

		for box in self.input_boxes:
			box.draw(self.screen)

		self.status_box.draw(self.screen, gameStatus)

		vpMousePos = pg.mouse.get_pos() - self.vpPos if self.vpRect.collidepoint(pg.mouse.get_pos()) else None
		self.gamecontroller.draw(self.vp, vpMousePos)

		# finalVp = pg.Surface((self.vpRect.width, self.vpRect.height), pg.SRCALPHA)
		# zoomedVp = pg.transform.scale(self.vp, (self.vpRect.width * self.zoom, self.vpRect.height * self.zoom))
		# finalVp.blit(zoomedVp, (self.scroll, 0))

		self.screen.blit(self.vp, self.vpPos)

	def getNewBoardValues(self):
		waterFloat = tryfloat(self.input_boxes[0].text)
		portFloat = tryfloat(self.input_boxes[1].text)
		townFloat = tryfloat(self.input_boxes[2].text)
		return waterFloat, portFloat, townFloat


def main():
	pg.init()
	GAME_FONT = pg.freetype.Font(os.path.join(os.path.dirname(__file__), "RobotoMono-VariableFont_wght.ttf"), 24)
	render = MainRender(GAME_FONT, 12, 12)
	render.start_mainloop()
	pg.quit()


if __name__ == '__main__':
	main()
	# cProfile.run('main()')