import pygame as pg
from renders.inputrender import GInputBox

PANEL_BG = pg.Color(45, 45, 48)
PANEL_BORDER = pg.Color(80, 80, 85)
BUTTON_BG = pg.Color(100, 100, 105)
BUTTON_HOVER = pg.Color(130, 130, 135)
LABEL_COLOR = pg.Color(220, 220, 220)
PANEL_W = 280
PANEL_H = 200
BUTTON_W = 90
BUTTON_H = 32
BUTTON_X = 10
BUTTON_Y = 9
PADDING = 18
ROW_H = 48


class GSettingsPanel:
    def __init__(self, GAME_FONT, screen_size):
        self.GAME_FONT = GAME_FONT
        self.screen_size = screen_size
        self.is_open = False

        self.button_rect = pg.Rect(BUTTON_X, BUTTON_Y, BUTTON_W, BUTTON_H)

        panel_x = BUTTON_X
        panel_y = BUTTON_Y + BUTTON_H + 6
        self.panel_rect = pg.Rect(panel_x, panel_y, PANEL_W, PANEL_H)

        input_x = panel_x + PADDING + 80
        input_w = PANEL_W - PADDING * 2 - 80

        self.water_box = GInputBox(GAME_FONT, input_x, panel_y + PADDING, input_w, 28)
        self.port_box = GInputBox(GAME_FONT, input_x, panel_y + PADDING + ROW_H, input_w, 28)
        self.town_box = GInputBox(GAME_FONT, input_x, panel_y + PADDING + ROW_H * 2, input_w, 28)
        self.input_boxes = [self.water_box, self.port_box, self.town_box]

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN:
            if self.button_rect.collidepoint(event.pos):
                self.is_open = not self.is_open
                return True
            if self.is_open:
                if not self.panel_rect.collidepoint(event.pos):
                    self.is_open = False
                    return True

        if self.is_open:
            for box in self.input_boxes:
                box.handle_event(event)
            return True

        return False

    def draw(self, screen):
        mouse_pos = pg.mouse.get_pos()
        btn_color = BUTTON_HOVER if self.button_rect.collidepoint(mouse_pos) else BUTTON_BG
        pg.draw.rect(screen, btn_color, self.button_rect, border_radius=4)
        label_surf, label_bb = self.GAME_FONT.render("Settings", LABEL_COLOR, size=9)
        lx = self.button_rect.x + (BUTTON_W - label_bb.w) // 2
        ly = self.button_rect.y + (BUTTON_H - label_bb.h) // 2
        screen.blit(label_surf, (lx, ly))

        if not self.is_open:
            return

        shadow = pg.Surface((PANEL_W + 6, PANEL_H + 6), pg.SRCALPHA)
        shadow.fill((0, 0, 0, 60))
        screen.blit(shadow, (self.panel_rect.x - 3, self.panel_rect.y - 3))

        pg.draw.rect(screen, PANEL_BG, self.panel_rect, border_radius=6)
        pg.draw.rect(screen, PANEL_BORDER, self.panel_rect, width=1, border_radius=6)

        labels = ["Water", "Port", "Town"]
        for i, (box, text) in enumerate(zip(self.input_boxes, labels)):
            surf, bb = self.GAME_FONT.render(text, LABEL_COLOR, size=9)
            lx = self.panel_rect.x + PADDING
            ly = box.rect.y + (box.rect.h - bb.h) // 2
            screen.blit(surf, (lx, ly))
            box.draw(screen)

    def get_values(self):
        def tryfloat(s):
            try:
                return float(s)
            except ValueError:
                return None

        return (
            tryfloat(self.water_box.text),
            tryfloat(self.port_box.text),
            tryfloat(self.town_box.text),
        )
