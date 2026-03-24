import pygame
import sys
import math
import random
import requests
from logger import (
    log_shot_fired, log_reload, log_dash, log_aoe_used,
    log_player_death, log_room_cleared, log_room_entered,
    log_game_over
)

# --- Inicializace ---
pygame.init()
SCREEN = pygame.display.set_mode((1920, 1080)) 
WIDTH, HEIGHT = 1920, 1080
pygame.display.set_caption("Speed Hell - Pygame Edition")
CLOCK = pygame.time.Clock()

# --- Barvy ---
WHITE = (255, 255, 255)
RED = (200, 50, 50)
GREEN = (50, 200, 50)
YELLOW = (220, 220, 50)
PURPLE = (150, 50, 150)
GRAY = (30, 30, 30)
DARK_RED = (150, 0, 0)
HOVER_RED = (200, 0, 0)
BORDER_THICKNESS = 60
TILE_SCALE = 3  # Kolikrát větší budou dlaždice (zvyšuj pokud jsou stále moc malé)
BLACK = (0, 0, 0)
BLOOD_RED = (120, 0, 0)
HELL_ORANGE = (200, 70, 0)
RESOLUTIONS = [
    (1920, 1080),
    (1600, 900), 
    (800, 600)
]
MAX_ROOMS = 3

# --- Herní stav ---
main_menu = True
in_starter_room = False
paused = False
show_settings = False
game_over = False
show_login = False
user_name = ""
user_pass = ""
active_field = "name"
MAX_ENEMIES = 15
spawn_cooldown = 500
last_spawn_time = 0
player_shoot_cooldown = 1
score = 0
room_count = 1
accumulated_time = 0
total_spawned = 0
arena_start_time = 0
elapsed_ms = 0
game_start_time = 0
starter_timer = 0
room_cleared = False
time_str = "TIME: 0:000"

# Načtení surových obrázků
WALL_TOP_RAW = pygame.image.load("assets/map/walls/tile033.png").convert_alpha()
WALL_BOTTOM_RAW = pygame.image.load("assets/map/walls/tile026.png").convert_alpha()
WALL_LEFT_RAW = pygame.image.load("assets/map/walls/tile013.png").convert_alpha()
WALL_RIGHT_RAW = pygame.image.load("assets/map/walls/tile016.png").convert_alpha()
FLOOR_RAW = pygame.image.load("assets/map/walls/tile017.png").convert_alpha()

# Animace AoE schopnosti (frame0000.png až frame0015.png)
AOE_FRAMES = []
for _i in range(16):
    _img = pygame.image.load(f"assets/player/aoe/frame{_i:04d}.png").convert_alpha()
    AOE_FRAMES.append(_img)

FLOOR_TILE_SIZE = 64  # Velikost jedné dlaždice podlahy v pixelech — uprav dle libosti

floor_tile = None

def update_floor_texture():
    global floor_tile
    floor_tile = pygame.transform.scale(FLOOR_RAW, (FLOOR_TILE_SIZE, FLOOR_TILE_SIZE))

def draw_floor(surface):
    """Vykreslí podlahu dlaždicováním uvnitř arény (bez borderu)."""
    x0 = BORDER_THICKNESS
    y0 = BORDER_THICKNESS
    area_w = WIDTH  - BORDER_THICKNESS * 2
    area_h = HEIGHT - BORDER_THICKNESS * 2
    clip_rect = pygame.Rect(x0, y0, area_w, area_h)
    old_clip = surface.get_clip()
    surface.set_clip(clip_rect)
    cols = (area_w // FLOOR_TILE_SIZE) + 2
    rows = (area_h // FLOOR_TILE_SIZE) + 2
    for row in range(rows):
        for col in range(cols):
            surface.blit(floor_tile, (x0 + col * FLOOR_TILE_SIZE, y0 + row * FLOOR_TILE_SIZE))
    surface.set_clip(old_clip)

wall_top, wall_bottom, wall_left, wall_right = None, None, None, None

def update_wall_textures():
    global wall_top, wall_bottom, wall_left, wall_right
    orig_w, orig_h = WALL_TOP_RAW.get_size()
    # Horizontální zdi: výška = BORDER_THICKNESS, šířka proporcionální * TILE_SCALE
    scale_h = BORDER_THICKNESS / orig_h
    tile_w = max(1, int(orig_w * scale_h * TILE_SCALE))
    wall_top    = pygame.transform.scale(WALL_TOP_RAW, (tile_w, BORDER_THICKNESS))
    wall_bottom = pygame.transform.flip(pygame.transform.scale(WALL_TOP_RAW, (tile_w, BORDER_THICKNESS)), False, True)
    # Vertikální zdi: šířka = BORDER_THICKNESS, výška proporcionální * TILE_SCALE
    orig_w2, orig_h2 = WALL_LEFT_RAW.get_size()
    scale_w = BORDER_THICKNESS / orig_w2
    tile_h = max(1, int(orig_h2 * scale_w * TILE_SCALE))
    wall_left  = pygame.transform.scale(WALL_LEFT_RAW,  (BORDER_THICKNESS, tile_h))
    wall_right = pygame.transform.scale(WALL_RIGHT_RAW, (BORDER_THICKNESS, tile_h))

def draw_tiled_wall(surface, tile, x, y, total_w, total_h):
    """Vykreslí dlaždice opakováním tile po celé ploše (x, y, total_w, total_h)."""
    tw, th = tile.get_size()
    # Ořezávací obdélník — aby tiles nepřetékaly za okraj zdi
    clip_rect = pygame.Rect(x, y, total_w, total_h)
    old_clip = surface.get_clip()
    surface.set_clip(clip_rect)
    cols = (total_w // tw) + 2
    rows = (total_h // th) + 2
    for row in range(rows):
        for col in range(cols):
            surface.blit(tile, (x + col * tw, y + row * th))
    surface.set_clip(old_clip)

update_wall_textures()
update_floor_texture()

def load_player_animations(path_prefix, count, size):
    images = []
    for i in range(count):
        img = pygame.image.load(f"{path_prefix}{i:03d}.png").convert_alpha()
        img = pygame.transform.scale(img, size)
        images.append(img)
    return images

PLAYER_WALK_IMAGES = load_player_animations("assets/player/tile", 6, (160, 160))
PLAYER_HURT_IMAGES = load_player_animations("assets/player/hurt/tile", 4, (160, 160))
PLAYER_DEATH_IMAGES = load_player_animations("assets/player/death/tile", 8, (160, 160))
BULLET_IMG = pygame.image.load("assets/player/attack/tile000.png").convert_alpha()
BULLET_IMG = pygame.transform.scale(BULLET_IMG, (30, 30))

def load_enemy_animations(path_prefix, start_idx, count, size):
    images = []
    for i in range(start_idx, start_idx + count):
        full_path = f"{path_prefix}tile{i:03d}.png"
        try:
            img = pygame.image.load(full_path).convert_alpha()
            img = pygame.transform.scale(img, size)
            images.append(img)
        except pygame.error:
            print(f"Varování: Soubor {full_path} nebyl nalezen!")
    return images

ENEMY_RED_WALK = load_enemy_animations("assets/enemies/melee/", 18, 6, (120, 120))
ENEMY_YELLOW_WALK = load_enemy_animations("assets/enemies/range/", 18, 6, (120, 120))
ENEMY_TANK_WALK = load_enemy_animations("assets/enemies/tank/", 18, 6, (140, 140))

# Animace střely ranged nepřítele (tile000 až tile047)
ENEMY_RANGE_ATTACK_FRAMES = []
for _i in range(48):
    _path = f"assets/enemies/range/attack/tile{_i:03d}.png"
    try:
        _img = pygame.image.load(_path).convert_alpha()
        _img = pygame.transform.scale(_img, (40, 40))
        ENEMY_RANGE_ATTACK_FRAMES.append(_img)
    except pygame.error:
        print(f"Varování: {_path} nebyl nalezen!")

font = pygame.font.SysFont("arial", 28)
title_font = pygame.font.SysFont("arial", 80, bold=True)

def handle_collision(obj1, obj2, force=10):
    dx = obj1.x - obj2.x
    dy = obj1.y - obj2.y
    dist = math.hypot(dx, dy)
    if dist < (obj1.size/2 + obj2.size/2):
        if dist == 0: dist = 0.1
        push_x = (dx / dist) * force
        push_y = (dy / dist) * force
        obj1.x += push_x
        obj1.y += push_y
        obj2.x -= push_x
        obj2.y -= push_y

class Entity:
    def __init__(self, x, y, size, color, speed):
        self.x, self.y = x, y
        self.size, self.color = size, color
        self.speed = speed

    def draw(self):
        pygame.draw.rect(SCREEN, self.color, (int(self.x), int(self.y), self.size, self.size))

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.size, self.size)

class Player(Entity):
    def __init__(self, x, y, size, color, speed):
        super().__init__(x, y, size, color, speed)
        self.rect = pygame.Rect(x, y - 50, 40, 70)
        self.hp = 3
        self.inv_timer = 0
        self.max_ammo = 10
        self.current_ammo = 10
        self.is_reloading = False
        self.reload_timer = 0
        self.reload_duration = 60
        self.dash_timer = 0
        self.dash_cooldown = 0
        self.dash_speed = speed * 4
        self.dash_direction = (0, 0)
        self.frame_index = 0
        self.animation_speed = 0.15
        self.is_moving = False
        self.facing_right = True
        self.animation_list = PLAYER_WALK_IMAGES
        self.image = self.animation_list[0]
        self.last_aoe_time = -10000
        self.aoe_radius = 250
        self.aoe_visual_timer = 0
        self.aoe_frame_index = 0.0  # Aktuální snímek animace AoE
        self.aoe_playing = False     # Zda animace právě běží
        self.is_dead = False
        self.death_timer = 0
        self.death_frame_index = 0

    def update_animation(self):
        if self.is_dead:
            current_anim_list = PLAYER_DEATH_IMAGES
            self.death_frame_index += 0.1
            if self.death_frame_index >= len(current_anim_list):
                self.death_frame_index = len(current_anim_list) - 1
            self.image = current_anim_list[int(self.death_frame_index)]
            return
        
        if self.inv_timer > 0:
            current_anim_list = PLAYER_HURT_IMAGES
        else:
            current_anim_list = PLAYER_WALK_IMAGES

        if self.is_moving or self.inv_timer > 0:
            self.frame_index += self.animation_speed
            if self.frame_index >= len(current_anim_list):
                self.frame_index = 0
        else:
            self.frame_index = 0

        self.image = current_anim_list[int(self.frame_index)]

    def reload(self):
        if self.current_ammo < self.max_ammo and not self.is_reloading:
            self.is_reloading = True
            self.reload_timer = self.reload_duration

    def update_reload(self):
        if self.is_reloading:
            self.reload_timer -= 1
            if self.reload_timer <= 0:
                self.current_ammo = self.max_ammo
                self.is_reloading = False

    def take_damage(self):
        if self.inv_timer == 0 and not self.is_dead:
            self.hp -= 1
            if self.hp <= 0:
                self.hp = 0
                self.is_dead = True
                self.death_timer = 300
                log_player_death(room_count, score, accumulated_time)
            else:
                self.inv_timer = 60

    def move(self, allow_exit=False):
        if self.is_dead:
            if self.death_timer > 0:
                self.death_timer -= 1
            self.update_animation()
            return
        
        win_w, win_h = SCREEN.get_size()
        keys = pygame.key.get_pressed()
        self.is_moving = False

        if self.inv_timer > 0: self.inv_timer -= 1
        if self.dash_cooldown > 0: self.dash_cooldown -= 1
        if self.dash_timer > 0: self.dash_timer -= 1

        dx = dy = 0
        if keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_s]: dy += 1
        if keys[pygame.K_a]: dx -= 1; self.facing_right = False
        if keys[pygame.K_d]: dx += 1; self.facing_right = True

        if keys[pygame.K_SPACE] and self.dash_cooldown <= 0 and (dx != 0 or dy != 0):
            self.dash_timer = 10
            self.dash_cooldown = 50
            length = math.hypot(dx, dy)
            self.dash_direction = (dx / length, dy / length)
            log_dash()

        current_speed = self.speed
        move_dir_x, move_dir_y = dx, dy

        if self.dash_timer > 0:
            current_speed = self.dash_speed
            move_dir_x, move_dir_y = self.dash_direction
            self.is_moving = True

        if move_dir_x != 0 or move_dir_y != 0:
            self.is_moving = True
            if self.dash_timer == 0:
                length = math.hypot(move_dir_x, move_dir_y)
                move_dir_x /= length
                move_dir_y /= length

        self.x += move_dir_x * current_speed
        self.y += move_dir_y * current_speed
        
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

        if self.rect.top < BORDER_THICKNESS:
            self.rect.top = BORDER_THICKNESS
            self.y = float(self.rect.y)
        
        if self.rect.bottom > win_h - BORDER_THICKNESS:
            self.rect.bottom = win_h - BORDER_THICKNESS
            self.y = float(self.rect.y)
            
        if self.rect.left < BORDER_THICKNESS:
            self.rect.left = BORDER_THICKNESS
            self.x = float(self.rect.x)

        d_h = win_h // 4
        door_top = win_h // 2 - d_h // 2
        door_bottom = win_h // 2 + d_h // 2
        in_door_y = door_top < self.rect.centery < door_bottom

        if not (allow_exit and in_door_y):
            if self.rect.right > win_w - BORDER_THICKNESS:
                self.rect.right = win_w - BORDER_THICKNESS
                self.x = float(self.rect.x)

        self.update_animation()

    def draw(self):
        if self.inv_timer > 0 and (self.inv_timer // 5) % 2 == 0: return
        
        display_img = self.image
        
        if not self.facing_right:
            display_img = pygame.transform.flip(display_img, True, False)

        img_rect = display_img.get_rect(center=self.rect.center)
        img_rect.y += 15 
        SCREEN.blit(display_img, img_rect)

class Enemy(Entity):
    def __init__(self, x, y, size, color, speed, hp=1, anim_list=None):
        super().__init__(x, y, size, color, speed)
        self.hp = hp
        self.rect = pygame.Rect(x, y, size, size)
        self.animation_list = anim_list
        self.frame_index = 0
        self.animation_speed = 0.15
        self.facing_right = True

    def follow(self, player):
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        
        if dist != 0:
            if dx > 5: self.facing_right = True
            elif dx < -5: self.facing_right = False
            
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed
            
            self.rect.x = int(self.x)
            self.rect.y = int(self.y)
            
            if self.animation_list:
                self.frame_index += self.animation_speed
                if self.frame_index >= 5:
                    self.frame_index = 0

    def draw(self):
        if self.animation_list:
            img = self.animation_list[int(self.frame_index)]
            if not self.facing_right:
                img = pygame.transform.flip(img, True, False)
            img_rect = img.get_rect(center=self.rect.center)
            SCREEN.blit(img, img_rect)

class RangedEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 40, YELLOW, 2, hp=1, anim_list=ENEMY_YELLOW_WALK)
        self.shoot_delay = 0
        self.range = 400
        self.rect = pygame.Rect(x, y, 50, 50)
   
    def follow(self, player):
        dx, dy = player.x - self.x, player.y - self.y
        dist = math.hypot(dx, dy)
        if dist > self.range: 
            super().follow(player)
        elif dist < self.range - 100:
            if dist != 0:
                self.x -= (dx / dist) * self.speed
                self.y -= (dy / dist) * self.speed
                self.facing_right = True if dx > 0 else False

        self.frame_index += self.animation_speed
        if self.frame_index >= len(self.animation_list):
            self.frame_index = 0
        
        self.shoot_delay += 1
        if self.shoot_delay >= 60:
            enemy_projectiles.append(EnemyProjectile(
                self.x + self.size/2, self.y + self.size/2,
                player.x + player.size/2, player.y + player.size/2,
                speed=6
            ))
            self.shoot_delay = 0
        self.rect.topleft = (int(self.x), int(self.y))


class TankEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 70, PURPLE, 1.2, hp=4, anim_list=ENEMY_TANK_WALK)

    def follow(self, player):
        super().follow(player)
        self.animation_speed = 0.1

class Projectile:
    def __init__(self, x, y, target_x, target_y, speed, color=None):
        self.x = x
        self.y = y
        self.speed = speed
        dx = target_x - x
        dy = target_y - y
        distance = math.hypot(dx, dy)
        self.dx = (dx / distance) * speed
        self.dy = (dy / distance) * speed
        angle = math.degrees(math.atan2(-dy, dx)) 
        self.image = pygame.transform.rotate(BULLET_IMG, angle)
        self.rect = self.image.get_rect(center=(x, y))

    def move(self):
        self.x += self.dx
        self.y += self.dy
        self.rect.center = (int(self.x), int(self.y))

    def draw(self):
        SCREEN.blit(self.image, self.rect)

    def collides_with(self, entity):
        return self.rect.colliderect(entity.rect)

class EnemyProjectile:
    """Animovaná střela ranged nepřítele."""
    def __init__(self, x, y, target_x, target_y, speed=6):
        self.x = x
        self.y = y
        self.speed = speed
        dx = target_x - x
        dy = target_y - y
        distance = math.hypot(dx, dy)
        self.dx = (dx / distance) * speed
        self.dy = (dy / distance) * speed
        # Úhel pro rotaci animace
        self.angle = math.degrees(math.atan2(-dy, dx))
        self.frame_index = 0.0
        self.animation_speed = 0.6
        self.rect = pygame.Rect(x - 20, y - 20, 40, 40)

    def move(self):
        self.x += self.dx
        self.y += self.dy
        self.rect.center = (int(self.x), int(self.y))
        # Posun animace
        self.frame_index += self.animation_speed
        if self.frame_index >= len(ENEMY_RANGE_ATTACK_FRAMES):
            self.frame_index = 0.0

    def draw(self):
        if not ENEMY_RANGE_ATTACK_FRAMES:
            pygame.draw.circle(SCREEN, YELLOW, (int(self.x), int(self.y)), 8)
            return
        frame = ENEMY_RANGE_ATTACK_FRAMES[int(self.frame_index)]
        rotated = pygame.transform.rotate(frame, self.angle)
        r = rotated.get_rect(center=(int(self.x), int(self.y)))
        SCREEN.blit(rotated, r)

    def collides_with(self, entity):
        return self.rect.colliderect(entity.rect)

def draw_button(text, x, y, w, h):
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()
    if x < mouse[0] < x + w and y < mouse[1] < y + h:
        pygame.draw.rect(SCREEN, HOVER_RED, (x, y, w, h), border_radius=10)
        if click[0] == 1: return True
    else:
        pygame.draw.rect(SCREEN, DARK_RED, (x, y, w, h), border_radius=10)
    label = font.render(text, True, WHITE)
    SCREEN.blit(label, (x + (w - label.get_width()) // 2, y + (h - label.get_height()) // 2))
    return False

def spawn_enemy():
    safe_min_x = BORDER_THICKNESS + 50
    safe_max_x = WIDTH - BORDER_THICKNESS - 100
    safe_min_y = BORDER_THICKNESS + 50
    safe_max_y = HEIGHT - BORDER_THICKNESS - 100

    x = random.randint(safe_min_x, safe_max_x)
    y = random.randint(safe_min_y, safe_max_y)
    
    while math.hypot(x - player.x, y - player.y) < 300:
        x = random.randint(safe_min_x, safe_max_x)
        y = random.randint(safe_min_y, safe_max_y)

    etype = random.random()
    if etype < 0.6: 
        return Enemy(x, y, 50, RED, 3.5, anim_list=ENEMY_RED_WALK)
    elif etype < 0.85: 
        return RangedEnemy(x, y)
    else: 
        return TankEnemy(x, y)

def verify_login_with_django(username, password):
    url = "http://127.0.0.1:8000/api/login/"
    payload = {"username": username, "password": password}
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            global user_name
            user_name = username 
            return True
        return False
    except:
        return False
    
def resolution_menu(screen):
    menu_running = True
    selected_res = None
    
    button_width, button_height = 250, 50
    buttons = []
    curr_w, curr_h = screen.get_size()
    
    for i, res in enumerate(RESOLUTIONS):
        rect = pygame.Rect(
            curr_w // 2 - button_width // 2,
            150 + i * 80,
            button_width,
            button_height
        )
        buttons.append((rect, res))

    while menu_running:
        screen.fill((30, 30, 30))
        
        title = font.render("Vyberte rozlišení hry:", True, (255, 255, 255))
        screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, 100))

        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                for rect, res in buttons:
                    if rect.collidepoint(mouse_pos):
                        selected_res = res
                        menu_running = False

        for rect, res in buttons:
            color = (189, 39, 47) if rect.collidepoint(mouse_pos) else (105, 2, 5)
            pygame.draw.rect(screen, color, rect, border_radius=10)
            text = font.render(f"{res[0]}x{res[1]}", True, (255, 255, 255))
            screen.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))

        pygame.display.flip()
    
    return selected_res

# --- Inicializace objektů ---
player = Player(WIDTH // 2, HEIGHT // 2, 40, GREEN, 6)
enemies, projectiles, enemy_projectiles = [], [], []


def send_time_to_django(username, time_ms):
    url = "http://127.0.0.1:8000/api/update_playtime/"
    payload = {"username": username, "play_time": time_ms}
    try:
        response = requests.post(url, json=payload, timeout=3)
        if response.status_code == 200:
            print(f"ÚSPĚCH: Čas {time_ms}ms uložen pro {username}")
        else:
            print(f"CHYBA DJANGA (Kód {response.status_code}): {response.text}")
    except Exception as e:
        print(f"Nepodařilo se spojit se serverem: {e}")


# --- Hlavní smyčka ---
running = True
while running:
    current_time = pygame.time.get_ticks()

    events = pygame.event.get() 
    for event in events:
        if event.type == pygame.QUIT: 
            running = False
  
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not main_menu and not game_over and not paused and not player.is_dead:
                if player.current_ammo > 0 and not player.is_reloading:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    projectiles.append(Projectile(
                        player.rect.centerx, 
                        player.rect.centery, 
                        mouse_x, 
                        mouse_y, 
                        speed=15, 
                    ))
                    player.current_ammo -= 1
                    log_shot_fired(player.current_ammo)
                    if player.current_ammo == 0:
                        player.reload()
                        log_reload(player.max_ammo)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                player.reload()
                log_reload(player.max_ammo)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if not main_menu and not game_over:
                    paused = not paused
                    show_settings = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                if not main_menu and not game_over and not paused:
                    if current_time - player.last_aoe_time >= 10000:
                        player.last_aoe_time = current_time
                        player.aoe_visual_timer = 15
                        player.aoe_playing = True
                        player.aoe_frame_index = 0.0
                        killed = 0
                        for e in enemies[:]:
                            dist = math.hypot(e.x - player.x, e.y - player.y)
                            if dist <= player.aoe_radius:
                                enemies.remove(e)
                                score += 100
                                killed += 1
                                if killed >= 5:
                                    break
                        log_aoe_used(killed, current_time)
                        if total_spawned >= MAX_ENEMIES and len(enemies) == 0:
                            room_cleared = True

        if main_menu and show_login:
            if event.type == pygame.MOUSEBUTTONDOWN:
                n_rect = pygame.Rect(WIDTH//2 - 150, 255, 300, 45)
                p_rect = pygame.Rect(WIDTH//2 - 150, 355, 300, 45)
                if n_rect.collidepoint(event.pos): active_field = "name"
                if p_rect.collidepoint(event.pos): active_field = "pass"

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    active_field = "pass" if active_field == "name" else "name"
                elif event.key == pygame.K_BACKSPACE:
                    if active_field == "name": user_name = user_name[:-1]
                    else: user_pass = user_pass[:-1]
                elif event.key == pygame.K_RETURN:
                    if user_name.strip() != "" and user_pass.strip() != "":
                        show_login = False
                        main_menu = False
                        in_starter_room = True
                        starter_timer = current_time
                else:
                    if event.unicode.isprintable():
                        if active_field == "name" and len(user_name) < 15:
                            user_name += event.unicode
                        elif active_field == "pass" and len(user_pass) < 15:
                            user_pass += event.unicode

    # --- VYKRESLOVÁNÍ ---
    SCREEN.fill(GRAY)

    # 1. HLAVNÍ MENU
    if main_menu:
        if show_login:
            txt = title_font.render("PŘIHLÁŠENÍ", True, WHITE)
            SCREEN.blit(txt, (WIDTH//2 - txt.get_width()//2, 100))
            
            name_label = font.render("Uživatelské jméno:", True, WHITE)
            SCREEN.blit(name_label, (WIDTH//2 - 150, 220))
            name_rect = pygame.Rect(WIDTH//2 - 150, 255, 300, 45)
            name_border_col = RED if active_field == "name" else BLACK
            pygame.draw.rect(SCREEN, name_border_col, name_rect, 2, border_radius=5)
            SCREEN.blit(font.render(user_name, True, WHITE), (name_rect.x + 10, name_rect.y + 7))

            pass_label = font.render("Heslo:", True, WHITE)
            SCREEN.blit(pass_label, (WIDTH//2 - 150, 320))
            pass_rect = pygame.Rect(WIDTH//2 - 150, 355, 300, 45)
            pass_border_col = RED if active_field == "pass" else BLACK
            pygame.draw.rect(SCREEN, pass_border_col, pass_rect, 2, border_radius=5)
            hidden_pass = "*" * len(user_pass)
            SCREEN.blit(font.render(hidden_pass, True, WHITE), (pass_rect.x + 10, pass_rect.y + 7))

            if draw_button("VSTOUPIT", WIDTH//2 - 125, 460, 250, 60):
                if user_name.strip() != "" and user_pass.strip() != "":
                    if verify_login_with_django(user_name, user_pass): 
                        chosen_res = resolution_menu(SCREEN)
                        
                        if chosen_res == (1920, 1080):
                            SCREEN = pygame.display.set_mode(chosen_res, pygame.FULLSCREEN)
                        else:
                            SCREEN = pygame.display.set_mode(chosen_res)
                        
                        WIDTH, HEIGHT = chosen_res
                        update_wall_textures()
                        update_floor_texture()
                        
                        player.x, player.y = WIDTH // 2, HEIGHT // 2
                        
                        show_login = False
                        main_menu = False
                        in_starter_room = True
                        starter_timer = pygame.time.get_ticks()
                    else:
                        user_pass = ""
                        print("Chybné údaje!")

            if draw_button("ZPĚT", WIDTH//2 - 125, 540, 250, 60):
                show_login = False
                pygame.time.delay(150)

        elif show_settings:
            txt = title_font.render("OVLÁDÁNÍ", True, YELLOW)
            SCREEN.blit(txt, (WIDTH//2 - txt.get_width()//2, 150))
            controls = ["W,A,S,D - Pohyb", "LMB - Střelba", "ESC - Pauza", "---", "Jdi do dveří vpravo!"]
            for i, line in enumerate(controls):
                SCREEN.blit(font.render(line, True, WHITE), (WIDTH//2 - 100, 300 + i * 40))
            if draw_button("ZPĚT", WIDTH//2 - 100, HEIGHT - 150, 200, 60):
                show_settings = False
                pygame.time.delay(150)

        else:
            txt = title_font.render("SPEED HELL", True, RED)
            SCREEN.blit(txt, (WIDTH//2 - txt.get_width()//2, 150))
            
            if draw_button("LOGIN", WIDTH//2 - 125, 350, 250, 60):
                show_login = True
                pygame.time.delay(150)
            
            if draw_button("NASTAVENÍ", WIDTH//2 - 125, 450, 250, 60):
                show_settings = True
                pygame.time.delay(150)
            
            if draw_button("UKONČIT", WIDTH//2 - 125, 550, 250, 60):
                running = False

    # 2. STARTER ROOM
    elif in_starter_room:
        d_h = HEIGHT // 4
        door_open = (current_time - starter_timer) > 2000
        player.move(allow_exit=door_open)

        # Vykreslení podlahy a textur stěn (dlaždicování)
        draw_floor(SCREEN)
        draw_tiled_wall(SCREEN, wall_top,    0, 0,                         WIDTH,            BORDER_THICKNESS)
        draw_tiled_wall(SCREEN, wall_bottom, 0, HEIGHT - BORDER_THICKNESS, WIDTH,            BORDER_THICKNESS)
        draw_tiled_wall(SCREEN, wall_left,   0, 0,                         BORDER_THICKNESS, HEIGHT)

        if not door_open:
            draw_tiled_wall(SCREEN, wall_right, WIDTH - BORDER_THICKNESS, 0, BORDER_THICKNESS, HEIGHT)
        else:
            door_top_px    = HEIGHT // 2 - d_h // 2
            door_bottom_px = HEIGHT // 2 + d_h // 2
            draw_tiled_wall(SCREEN, wall_right, WIDTH - BORDER_THICKNESS, 0,              BORDER_THICKNESS, door_top_px)
            draw_tiled_wall(SCREEN, wall_right, WIDTH - BORDER_THICKNESS, door_bottom_px, BORDER_THICKNESS, HEIGHT - door_bottom_px)
            
            if (current_time // 250) % 2 == 0:
                pygame.draw.rect(SCREEN, GREEN, (WIDTH - BORDER_THICKNESS, HEIGHT // 2 - d_h // 2, BORDER_THICKNESS, d_h))

        # Vykreslení hráče
        player.draw()

        if player.aoe_playing:
            frame = AOE_FRAMES[int(player.aoe_frame_index)]
            frame_scaled = pygame.transform.scale(frame, (player.aoe_radius * 2, player.aoe_radius * 2))
            frame_rect = frame_scaled.get_rect(center=player.rect.center)
            SCREEN.blit(frame_scaled, frame_rect)
            player.aoe_frame_index += 0.4
            if player.aoe_frame_index >= len(AOE_FRAMES):
                player.aoe_frame_index = 0.0
                player.aoe_playing = False

        # Detekce průchodu
        door_top = HEIGHT // 2 - d_h // 2
        door_bottom = HEIGHT // 2 + d_h // 2
    
        if door_open and player.rect.right > WIDTH - BORDER_THICKNESS:
            if door_top < player.rect.centery < door_bottom:
                in_starter_room = False
                game_start_time = current_time
                arena_start_time = pygame.time.get_ticks()
                player.x = BORDER_THICKNESS + 20 
                player.rect.x = int(player.x)
                pygame.time.delay(100)

    # 3. SAMOTNÁ HRA (ARÉNA)
    elif not game_over:
        d_h = HEIGHT // 4
        
        if not paused:
            player.move(allow_exit=room_cleared)
            player.update_reload()

        if player.is_dead and player.death_timer <= 0:
            log_game_over(victory=False, score=score, time_ms=accumulated_time + (current_time - arena_start_time))
            game_over = True

        # Časovač
        total_elapsed_ms = accumulated_time + (current_time - arena_start_time)
        seconds = total_elapsed_ms // 1000
        milis = total_elapsed_ms % 1000
        time_str = f"TIME: {seconds}:{milis:03d}"

        # Přechod do další místnosti
        if room_cleared and player.rect.right > WIDTH - BORDER_THICKNESS:
            if room_count < MAX_ROOMS:
                accumulated_time += (pygame.time.get_ticks() - arena_start_time)
                log_room_cleared(room_count, accumulated_time)
                room_cleared = False
                total_spawned = 0
                enemies = []
                projectiles = []
                enemy_projectiles = []
                player.x = 80 
                player.rect.x = int(player.x)
                room_count += 1
                MAX_ENEMIES += 6
                spawn_cooldown = max(500, spawn_cooldown - 200)
                arena_start_time = pygame.time.get_ticks()
                log_room_entered(room_count)
                pygame.time.delay(100)
            else:
                final_total_time = accumulated_time + (pygame.time.get_ticks() - arena_start_time)
                log_room_cleared(room_count, final_total_time)
                log_game_over(victory=True, score=score, time_ms=final_total_time)
                send_time_to_django(user_name, final_total_time)
                game_over = True

        # Spawnování nepřátel
        if current_time - arena_start_time > 2000:
            if total_spawned < MAX_ENEMIES and current_time - last_spawn_time > spawn_cooldown:
                enemies.append(spawn_enemy())
                total_spawned += 1
                last_spawn_time = current_time

        # Logika projektilů (hráčovy střely)
        for p in projectiles[:]:
            p.move()
            if not (0 <= p.x <= WIDTH and 0 <= p.y <= HEIGHT): 
                projectiles.remove(p)
            else:
                for e in enemies[:]:
                    if p.collides_with(e):
                        e.hp -= 1
                        if p in projectiles: projectiles.remove(p)
                        if e.hp <= 0: 
                            enemies.remove(e)
                            score += 100
                            if total_spawned >= MAX_ENEMIES and len(enemies) == 0:
                                room_cleared = True
                        break

        # Logika nepřátelských střel
        for ep in enemy_projectiles[:]:
            ep.move()
            if ep.collides_with(player): 
                player.take_damage()
                enemy_projectiles.remove(ep)
            elif not (0 <= ep.x <= WIDTH and 0 <= ep.y <= HEIGHT): 
                enemy_projectiles.remove(ep)

        # Logika nepřátel a kolize
        for e in enemies:
            if not player.is_dead:
                e.follow(player)
                if player.rect.colliderect(e.rect):
                    player.take_damage()
                    handle_collision(player, e, force=20)
                    player.x = max(BORDER_THICKNESS, min(WIDTH - BORDER_THICKNESS - player.rect.width, player.x))
                    player.y = max(BORDER_THICKNESS, min(HEIGHT - BORDER_THICKNESS - player.rect.height, player.y))
                    player.rect.x, player.rect.y = int(player.x), int(player.y)
            
            for other_e in enemies:
                if e != other_e and e.rect.colliderect(other_e.rect):
                    handle_collision(e, other_e, force=8)

        # --- VYKRESLOVÁNÍ ARÉNY ---
        draw_floor(SCREEN)
        draw_tiled_wall(SCREEN, wall_top,    0, 0,                         WIDTH,            BORDER_THICKNESS)
        draw_tiled_wall(SCREEN, wall_bottom, 0, HEIGHT - BORDER_THICKNESS, WIDTH,            BORDER_THICKNESS)
        draw_tiled_wall(SCREEN, wall_left,   0, 0,                         BORDER_THICKNESS, HEIGHT)

        if not room_cleared:
            draw_tiled_wall(SCREEN, wall_right, WIDTH - BORDER_THICKNESS, 0, BORDER_THICKNESS, HEIGHT)
        else:
            door_top = HEIGHT // 2 - d_h // 2
            door_bottom = HEIGHT // 2 + d_h // 2
            draw_tiled_wall(SCREEN, wall_right, WIDTH - BORDER_THICKNESS, 0,           BORDER_THICKNESS, door_top)
            draw_tiled_wall(SCREEN, wall_right, WIDTH - BORDER_THICKNESS, door_bottom, BORDER_THICKNESS, HEIGHT - door_bottom)
            if (current_time // 250) % 2 == 0:
                pygame.draw.rect(SCREEN, GREEN, (WIDTH - BORDER_THICKNESS, door_top, BORDER_THICKNESS, d_h))

        # Entity
        for p in projectiles: p.draw()
        for ep in enemy_projectiles: ep.draw()
        for e in enemies: e.draw()
        player.draw()

        # AoE animace
        if player.aoe_playing:
            frame = AOE_FRAMES[int(player.aoe_frame_index)]
            frame_scaled = pygame.transform.scale(frame, (player.aoe_radius * 2, player.aoe_radius * 2))
            frame_rect = frame_scaled.get_rect(center=player.rect.center)
            SCREEN.blit(frame_scaled, frame_rect)
            player.aoe_frame_index += 0.4
            if player.aoe_frame_index >= len(AOE_FRAMES):
                player.aoe_frame_index = 0.0
                player.aoe_playing = False

        # HUD
        hud_width, hud_height = 280, 100
        hud_x = WIDTH - hud_width - 10
        hud_y = HEIGHT - hud_height - 10

        hud_rect = pygame.Rect(hud_x, hud_y, hud_width, hud_height)
        pygame.draw.rect(SCREEN, BLACK, hud_rect)
        pygame.draw.rect(SCREEN, BLOOD_RED, hud_rect, 0, border_radius=8)
        pygame.draw.rect(SCREEN, HELL_ORANGE, hud_rect, 3, border_radius=8)

        life_text = font.render(f"HP:", True, WHITE)
        SCREEN.blit(life_text, (hud_x + 15, hud_y + 15))
        
        for i in range(3):
            heart_rect = pygame.Rect(hud_x + 60 + (i * 35), hud_y + 18, 25, 25)
            if i < player.hp:
                pygame.draw.rect(SCREEN, RED, heart_rect, 0, border_radius=4)
            else:
                pygame.draw.rect(SCREEN, GRAY, heart_rect, 2, border_radius=4)

        ammo_color = WHITE if not player.is_reloading else YELLOW
        ammo_label = "RELOADING..." if player.is_reloading else f"AMMO: {player.current_ammo}/{player.max_ammo}"
        ammo_render = font.render(ammo_label, True, ammo_color)
        SCREEN.blit(ammo_render, (hud_x + 15, hud_y + 55))

        if player.is_reloading:
            reload_bar_width = (player.reload_timer / player.reload_duration) * (hud_width - 30)
            pygame.draw.rect(SCREEN, YELLOW, (hud_x + 15, hud_y + 85, reload_bar_width, 5))

        SCREEN.blit(font.render(f"Místnost: {room_count} / {MAX_ROOMS}", True, YELLOW), (20, 50))
        SCREEN.blit(font.render(f"Skóre: {score}", True, WHITE), (20, 90))

        time_render = font.render(time_str, True, WHITE)
        SCREEN.blit(time_render, (20, 20))

        # Dash cooldown ukazatel
        dash_color = GREEN if player.dash_cooldown <= 0 else RED
        pygame.draw.rect(SCREEN, GRAY, (20, 130, 100, 10))
        if player.dash_cooldown > 0:
            charge_w = 100 - (player.dash_cooldown * 2)
            pygame.draw.rect(SCREEN, dash_color, (20, 130, max(0, charge_w), 10))
        else:
            pygame.draw.rect(SCREEN, dash_color, (20, 130, 100, 10))

        # AoE cooldown ukazatel
        aoe_time_passed = current_time - player.last_aoe_time
        aoe_color = (0, 255, 255) if aoe_time_passed >= 10000 else RED
        pygame.draw.rect(SCREEN, GRAY, (20, 150, 100, 10))
        if aoe_time_passed < 10000:
            aoe_charge_w = (aoe_time_passed / 10000) * 100
            pygame.draw.rect(SCREEN, aoe_color, (20, 150, max(0, aoe_charge_w), 10))
        else:
            pygame.draw.rect(SCREEN, aoe_color, (20, 150, 100, 10))

        # Pauza overlay
        if paused:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            SCREEN.blit(overlay, (0, 0))
            txt = title_font.render("PAUZA", True, WHITE)
            SCREEN.blit(txt, (WIDTH//2 - txt.get_width()//2, 200))
            if draw_button("ZPĚT DO HRY", WIDTH//2 - 125, 350, 250, 60): paused = False
            if draw_button("UKONČIT", WIDTH//2 - 125, 450, 250, 60): running = False

    # 4. GAME OVER
    else:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        
        if player.hp > 0:
            overlay.fill((0, 50, 0, 200))
            msg = "VICTORY!"
            color = (100, 255, 100)
        else:
            overlay.fill((50, 0, 0, 200))
            msg = "GAME OVER"
            color = WHITE
            
        SCREEN.blit(overlay, (0, 0))
        
        txt = title_font.render(msg, True, color)
        SCREEN.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 100))
        
        final_time_str = f"Konečný čas: {elapsed_ms // 1000}:{elapsed_ms % 1000:03d}s"
        time_txt = font.render(final_time_str, True, WHITE)
        SCREEN.blit(time_txt, (WIDTH//2 - time_txt.get_width()//2, HEIGHT//2))

        if draw_button("UKONČIT", WIDTH//2 - 100, HEIGHT//2 + 80, 200, 60): 
            running = False

    pygame.display.flip()
    CLOCK.tick(60)

pygame.quit()
sys.exit()