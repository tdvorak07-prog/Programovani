import pygame
import sys
import math
import random

# --- Inicializace ---
pygame.init()
WIDTH, HEIGHT = 1920, 1080
SCREEN = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = SCREEN.get_size()
pygame.display.set_caption("Jednoduchá Pygame Hra")
CLOCK = pygame.time.Clock()

# --- Barvy ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 50, 50)
BLUE = (50, 50, 200)
GRAY = (40, 40, 40)
LIGHT_GRAY = (100, 100, 100)

# --- Herní stav ---
paused = False
show_settings = False
MAX_ENEMIES = 5

# --- Fonty ---
font = pygame.font.SysFont("arial", 32)
title_font = pygame.font.SysFont("arial", 48, bold=True)

# --- Třídy ---
class Entity:
    def __init__(self, x, y, size, color, speed):
        self.x = x
        self.y = y
        self.size = size
        self.color = color
        self.speed = speed

    def draw(self):
        pygame.draw.rect(SCREEN, self.color, (self.x, self.y, self.size, self.size))

class Player(Entity):
    def move(self, enemies):
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_s]: dy += 1
        if keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_d]: dx += 1

        if dx != 0 or dy != 0:
            length = math.hypot(dx, dy)
            dx /= length
            dy /= length

        self.x += dx * self.speed
        self.y += dy * self.speed

        # Bordery
        self.x = max(0, min(WIDTH - self.size, self.x))
        self.y = max(0, min(HEIGHT - self.size, self.y))

        # Kolize s nepřáteli -> odraz
        for enemy in enemies:
            if self.collides_with(enemy):
                vec_x = self.x - enemy.x
                vec_y = self.y - enemy.y
                dist = math.hypot(vec_x, vec_y)
                if dist == 0:
                    dist = 1
                vec_x /= dist
                vec_y /= dist
                overlap = (self.size + enemy.size)/2
                self.x += vec_x * overlap
                self.y += vec_y * overlap


    def draw(self):
        pygame.draw.rect(SCREEN, self.color, (self.x, self.y, self.size, self.size))

    def collides_with(self, other):
        # AABB kolize
        return (self.x < other.x + other.size and
                self.x + self.size > other.x and
                self.y < other.y + other.size and
                self.y + self.size > other.y)
class Enemy(Entity):
    def follow(self, player, others):
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist != 0:
            dx /= dist
            dy /= dist
            new_x = self.x + dx * self.speed
            new_y = self.y + dy * self.speed

            # kontrola kolize s ostatními nepřáteli
            for other in others:
                if other == self:
                    continue
                if self.collides_at(new_x, new_y, other):
                    # Odrazíme nepřátele od sebe malou hodnotou
                    overlap_x = (self.x + self.size/2) - (other.x + other.size/2)
                    overlap_y = (self.y + self.size/2) - (other.y + other.size/2)
                    factor = 0.5  # minimalni odraz
                    new_x += factor * (1 if overlap_x >= 0 else -1)
                    new_y += factor * (1 if overlap_y >= 0 else -1)

            self.x, self.y = new_x, new_y

    def collides_at(self, x, y, other):
        return (x < other.x + other.size and
                x + self.size > other.x and
                y < other.y + other.size and
                y + self.size > other.y)

        

# --- Funkce pro tlačítka ---
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

# --- Inicializace hráče a nepřátel ---
player = Player(WIDTH // 2, HEIGHT // 2, 50, BLUE, 5)
enemies = [Enemy(random.randint(0, WIDTH-50), random.randint(0, HEIGHT-50), 50, RED, 3) for _ in range(MAX_ENEMIES)]

# --- Hlavní smyčka ---
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            paused = not paused
            show_settings = False

    SCREEN.fill((30, 30, 30))

    if not paused:
        # --- Pohyb hráče ---
        player.move(enemies)

        # --- Nepřátelé sledují hráče ---
        for enemy in enemies:
            enemy.follow(player, enemies)

        # --- Vykreslení ---
        player.draw()
        for enemy in enemies:
            enemy.draw()
    else:
        # --- Pauza menu ---
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
