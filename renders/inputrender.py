import pygame as pg
import pygame.freetype

class GInputBox:
	COLOR_ACTIVE = pg.Color("dodgerblue2")
	COLOR_INACTIVE = pg.Color("lightskyblue3")
	def __init__(self, GAME_FONT, x, y, w, h, text=""):
		self.GAME_FONT = GAME_FONT
		self.rect = pg.Rect(x, y, w, h)
		self.color = self.COLOR_INACTIVE
		self.text = text
		surface, bb = GAME_FONT.render(text, "black", size=9)
		self.text_surface = surface
		self.active = False

	def handle_event(self, event):
		if event.type == pg.MOUSEBUTTONDOWN:
			if self.rect.collidepoint(event.pos):
				self.active = not self.active
			else:
				self.active = False
			self.color = self.COLOR_ACTIVE if self.active else self.COLOR_INACTIVE
		if event.type == pg.KEYDOWN and self.active:
			if event.key == pg.K_BACKSPACE:
				self.text = self.text[:-1]
			elif pg.key.name(event.key).isdigit() or event.key == pg.K_PERIOD:
				self.text += event.unicode
			surface, bb = self.GAME_FONT.render(self.text, "black", size=9)
			self.text_surface = surface

	def draw(self, screen):
		pg.draw.rect(screen, self.color, self.rect)
		screen.blit(self.text_surface, (self.rect.x + 5, self.rect.y + 5))