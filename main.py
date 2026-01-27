import pygame
import sys
import math

# Inicializace 
pygame.init()
WIDTH = 1920
HEIGHT = 1080
SCREEN = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = SCREEN.get_size()
pygame.display.set_caption("Jednoduchá Pygame Hra")
CLOCK = pygame.time.Clock()

# Barvy 
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 50, 50)
GRAY = (40, 40, 40)
LIGHT_GRAY = (100, 100, 100)

# Hráč 
player_size = 50
player_pos = [900 // 2 - player_size // 2, 900 // 2 - player_size // 2]
player_speed = 5

# Herní stav 
paused = False
show_settings = False

#game map 
font = pygame.font.SysFont("arial", 32)
title_font = pygame.font.SysFont("arial", 48, bold=True)
level_map = [
    "10000000000"
    "01111001110",
    "00111000000",
    "00011111100",
    "00001110000",
    "01101111100",
    "01100000000",
    "01111111100"
    "00000011110",
]

#Map Size
MAP_WIDTH = len(level_map[0])     # columns
MAP_HEIGHT = len(level_map)       # rows

TILE_SIZE = min(
    WIDTH // MAP_WIDTH,
    HEIGHT // MAP_HEIGHT
)

WALL_COLOR = (120, 0, 0)
FLOOR_COLOR = (30, 30, 30)
def draw_level():
    offset_x = (WIDTH - MAP_WIDTH * TILE_SIZE) // 2
    offset_y = (HEIGHT - MAP_HEIGHT * TILE_SIZE) // 2

    for y, row in enumerate(level_map):
        for x, tile in enumerate(row):
            rect = pygame.Rect(
                offset_x + x * TILE_SIZE,
                offset_y + y * TILE_SIZE,
                TILE_SIZE,
                TILE_SIZE
            )

            if tile == "1":
                pygame.draw.rect(SCREEN, WALL_COLOR, rect)
            else:
                pygame.draw.rect(SCREEN, FLOOR_COLOR, rect)
# Tlačítka 
def draw_button(text, x, y, w, h):
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()
    color = LIGHT_GRAY if (x < mouse[0] < x + w and y < mouse[1] < y + h) else GRAY
    pygame.draw.rect(SCREEN, color, (x, y, w, h), border_radius=10)
    label = font.render(text, True, WHITE)
    SCREEN.blit(label, (x + w // 2 - label.get_width() // 2, y + h // 2 - label.get_height() // 2))
    if click[0] == 1 and (x < mouse[0] < x + w and y < mouse[1] < y + h):
        return True
    return False

# Hlavní smyčka
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                paused = not paused
                show_settings = False

    if not paused:
        # Pohyb hráče
        keys = pygame.key.get_pressed()
        move_x = 0
        move_y = 0

        if keys[pygame.K_w]:
            move_y -= 1
        if keys[pygame.K_s]:
            move_y += 1
        if keys[pygame.K_a]:
            move_x -= 1
        if keys[pygame.K_d]:
            move_x += 1

        # Diagonanlí pohyb = normální rychlost
        if move_x != 0 or move_y != 0:
            length = math.sqrt(move_x ** 2 + move_y ** 2)
            move_x /= length
            move_y /= length

        player_pos[0] += move_x * player_speed
        player_pos[1] += move_y * player_speed

        # Bordery
        player_pos[0] = max(0, min(WIDTH - player_size, player_pos[0]))
        player_pos[1] = max(0, min(HEIGHT - player_size, player_pos[1]))

        # Vykreslení
        SCREEN.fill((30, 30, 30))
        draw_level()
        pygame.draw.rect(SCREEN, RED, (player_pos[0], player_pos[1], player_size, player_size))
    else:
        # Menu
        SCREEN.fill((20, 20, 20))
        title = title_font.render("PAUZA", True, WHITE)
        SCREEN.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

        if not show_settings:
            if draw_button("Nastavení", WIDTH // 2 - 100, 250, 200, 60):
                show_settings = True
                pygame.time.wait(200)
            if draw_button("Ukončit", WIDTH // 2 - 100, 350, 200, 60):
                pygame.quit()
                sys.exit()
        else:
            text = font.render("Dash: SpaceBar + SpaceBar Ultimate ability: R + R", True, WHITE)
            SCREEN.blit(text, (WIDTH // 2 - text.get_width() // 2, 300))
            if draw_button("Zpět", WIDTH // 2 - 100, 400, 200, 60):
                show_settings = False
                pygame.time.wait(200)






    pygame.display.flip()
    CLOCK.tick(60)
