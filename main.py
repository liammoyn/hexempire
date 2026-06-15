import os
import asyncio
import pygame as pg
import pygame.freetype
import math
from renders.inputrender import GInputBox
from renders.statusrender import GStatus
from gamecontroller import GameStateController
from players.naive_player import NaivePlayer
from players.evaluation_player import EvaluationPlayer
from players.objective_player import ObjectivePlayer
from players.computer_wrapper import ComputerWrapper
from datatypes import GameProgress
from hexutils import calculateBoardDimensions

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

		self.computerPlayers = [
			ComputerWrapper(ObjectivePlayer(0), 0),
			ComputerWrapper(ObjectivePlayer(1), 1),
			ComputerWrapper(ObjectivePlayer(2), 2),
			ComputerWrapper(ObjectivePlayer(3), 3)
		]
		isUserPlayer = [False, False, False, False]

		self.clock = pg.time.Clock()
		startStepping = True
		self.gamecontroller = GameStateController(GAME_FONT, self.clock, cols, rows, hexW, hexH, isUserPlayer, startStepping)
		self.running = False
		self.savedGameState = None
		self.gameStatusHistory = [ self.gamecontroller.getGameStateString() ]
		self.isNewGame = True
		self.lastMoveCounter = None

		# self.zoom = 1
		# self.scroll = 0


	async def start_mainloop(self):
		self.gamecontroller.startGame()

		avgFps = 0
		fpss = 0

		timeRunning = 0
		self.running = True
		while self.running:
			self.clock.tick()

			self.handleEvents(pg.event.get())

			gameStatus = self.gamecontroller.getStatus()

			# Run AI move inline (replaces background threads)
			if (gameStatus.gameProgress == GameProgress.RUNNING
					and not self.gamecontroller.isUserPlayer[gameStatus.currentTurn]
					and gameStatus.moveCounter != self.lastMoveCounter
					and not self.gamecontroller.stepping):
				self.lastMoveCounter = gameStatus.moveCounter
				player = self.computerPlayers[gameStatus.currentTurn]
				move, moveEvals, objectiveEvals = player.requestMove(gameStatus.board, gameStatus.movesLeft)
				self.gamecontroller.handleComputerMove(move, gameStatus.currentTurn)
				self.gamecontroller.handleComputerEvals(moveEvals, objectiveEvals, gameStatus.currentTurn)
				gameStatus = self.gamecontroller.getStatus()

			if self.isNewGame:
				self.isNewGame = False
				self.lastMoveCounter = None

			self.draw(gameStatus)

			pg.display.flip()
			await asyncio.sleep(0)
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
					# In stepping mode, queue the next AI move then step it forward
					if self.gamecontroller.stepping:
						gameStatus = self.gamecontroller.getStatus()
						if (gameStatus.gameProgress == GameProgress.RUNNING
								and not self.gamecontroller.isUserPlayer[gameStatus.currentTurn]
								and self.gamecontroller.queuedMove is None):
							self.lastMoveCounter = gameStatus.moveCounter
							player = self.computerPlayers[gameStatus.currentTurn]
							move, moveEvals, objectiveEvals = player.requestMove(gameStatus.board, gameStatus.movesLeft)
							self.gamecontroller.handleComputerMove(move, gameStatus.currentTurn)
							self.gamecontroller.handleComputerEvals(moveEvals, objectiveEvals, gameStatus.currentTurn)
					self.gameStatusHistory.append(self.gamecontroller.getGameStateString())
					self.gamecontroller.handleStepForward()
				elif event.key == pg.K_LEFT and len(self.gameStatusHistory) > 1:
					lastGameState = self.gameStatusHistory.pop()
					self.gamecontroller.useGameStateString(lastGameState)
					self.lastMoveCounter = None
				elif event.key == pg.K_s:
					self.gamecontroller.toggleStepping()
				elif event.key == pg.K_p:
					self.savedGameState = self.gamecontroller.getGameStateString()
				elif event.key == pg.K_l and self.savedGameState is not None:
					self.gamecontroller.useGameStateString(self.savedGameState)
					self.lastMoveCounter = None
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


	def draw(self, gameStatus):
		self.screen.fill("white")
		self.vp.fill("white")

		for box in self.input_boxes:
			box.draw(self.screen)

		self.status_box.draw(self.screen, gameStatus)

		vpMousePos = pg.mouse.get_pos() - self.vpPos if self.vpRect.collidepoint(pg.mouse.get_pos()) else None
		self.gamecontroller.draw(self.vp, vpMousePos)

		self.screen.blit(self.vp, self.vpPos)

	def getNewBoardValues(self):
		waterFloat = tryfloat(self.input_boxes[0].text)
		portFloat = tryfloat(self.input_boxes[1].text)
		townFloat = tryfloat(self.input_boxes[2].text)
		return waterFloat, portFloat, townFloat


async def main():
	pg.init()
	GAME_FONT = pg.freetype.Font(os.path.join(os.path.dirname(__file__), "RobotoMono-VariableFont_wght.ttf"), 24)
	render = MainRender(GAME_FONT, 12, 12)
	await render.start_mainloop()
	pg.quit()


asyncio.run(main())
