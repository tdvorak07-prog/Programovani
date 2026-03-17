import pygame
import sys
import math
import random
import requests

# --- Inicializace ---
pygame.init()
SCREEN = pygame.display.set_mode((1920, 1080)) 
WIDTH, HEIGHT = 1920, 1080
pygame.display.set_caption("Speed Hell - Pygame Edition")
CLOCK = pygame.time.Clock()

# --- Barvy ---
WHITE = (255, 255, 255)
RED = (200, 50, 50)       # Základní / Top border
GREEN = (50, 200, 50)     # Hráč / Bottom border
YELLOW = (220, 220, 50)   # Ranged / Left border
PURPLE = (150, 50, 150)   # Tank / Right border
GRAY = (30, 30, 30)
DARK_RED = (150, 0, 0)
HOVER_RED = (200, 0, 0)
BORDER_THICKNESS = 15
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
active_field = "name"  # Může být "name" nebo "pass"
MAX_ENEMIES = 15          # Základní počet nepřátel zvýšen (původně 8)
spawn_cooldown = 500     # Milisekundy mezi spawny (1.5 sekundy)
last_spawn_time = 0
player_shoot_cooldown = 1
score = 0
total_spawned = 0
arena_start_time = 0
elapsed_ms = 0
game_start_time = 0      # Čas pro spawn nepřátel v hlavní hře
starter_timer = 0        # Čas pro otevření dveří v první místnosti
room_cleared = False
room_count = 1#  kolikátá  místnost
time_str = "TIME: 0:000"  # Přidej tento řádek



def load_player_animations(path_prefix, count, size):
    images = []
    for i in range(count):
        # Automaticky složí název: assets/player/tile000.png, tile001.png...
        img = pygame.image.load(f"{path_prefix}{i:03d}.png").convert_alpha()
        img = pygame.transform.scale(img, size)
        images.append(img)
    return images

PLAYER_WALK_IMAGES = load_player_animations("assets/player/tile", 6, (160, 160))
# --- Fonty ---
font = pygame.font.SysFont("arial", 28)
title_font = pygame.font.SysFont("arial", 80, bold=True)

# --- Pomocné funkce ---
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

# --- Třídy ---
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
        self.hp = 3
        self.inv_timer = 0
        # --- AMMO SYSTÉM ---
        self.max_ammo = 10
        self.current_ammo = 10
        self.is_reloading = False
        self.reload_timer = 0
        self.reload_duration = 60  # 1.5 sekundy (při 60 FPS)
        # -------------------
        self.dash_timer = 0
        self.dash_cooldown = 0
        self.dash_speed = speed * 4
        self.dash_direction = (0, 0)
       # --- ANIMACE ---
        self.animation_list = PLAYER_WALK_IMAGES
        self.frame_index = 0
        self.animation_speed = 0.15  # Rychlost střídání (čím vyšší, tím rychlejší)
        self.is_moving = False
        self.image = self.animation_list[self.frame_index]
        self.facing_right = True

    def update_animation(self):
        # Animujeme jen pokud se hráč hýbe
        if self.is_moving:
            self.frame_index += self.animation_speed
            if self.frame_index >= len(self.animation_list):
                self.frame_index = 0
        else:
            self.frame_index = 0 # Stojí na prvním snímku
        
        self.image = self.animation_list[int(self.frame_index)]

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
        if self.inv_timer == 0:
            self.hp -= 1
            self.inv_timer = 60  # Nezranitelný po dobu 1 sekundy (60 snímků)


    def move(self, allow_exit=False):
    # Získání aktuální velikosti okna (klíčové pro správné bordery)
        win_w, win_h = SCREEN.get_size()
        keys = pygame.key.get_pressed()
        
        self.is_moving = False

        # Timery
        if self.inv_timer > 0: self.inv_timer -= 1
        if self.dash_cooldown > 0: self.dash_cooldown -= 1
        if self.dash_timer > 0: self.dash_timer -= 1

        # Směr pohybu
        dx = dy = 0
        if keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_s]: dy += 1
        if keys[pygame.K_a]: dx -= 1; self.facing_right = False
        if keys[pygame.K_d]: dx += 1; self.facing_right = True

        # Dash logika
        if keys[pygame.K_SPACE] and self.dash_cooldown <= 0 and (dx != 0 or dy != 0):
            self.dash_timer = 10
            self.dash_cooldown = 50
            length = math.hypot(dx, dy)
            self.dash_direction = (dx / length, dy / length)

        current_speed = self.speed
        move_dir_x, move_dir_y = dx, dy

        if self.dash_timer > 0:
            current_speed = self.dash_speed
            move_dir_x, move_dir_y = self.dash_direction
            self.is_moving = True

        # Výpočet nové pozice
        if move_dir_x != 0 or move_dir_y != 0:
            self.is_moving = True
            if self.dash_timer == 0:
                length = math.hypot(move_dir_x, move_dir_y)
                move_dir_x /= length
                move_dir_y /= length

            # Aplikace pohybu
        self.x += move_dir_x * current_speed
        self.y += move_dir_y * current_speed

        # --- OPRAVENÉ HRANICE ---
        # Horní a spodní (vždy aktivní)
        if self.y < BORDER_THICKNESS:
            self.y = BORDER_THICKNESS
        elif self.y > win_h - BORDER_THICKNESS - self.size:
            self.y = win_h - BORDER_THICKNESS - self.size
            
        # Levá (vždy aktivní)
        if self.x < BORDER_THICKNESS:
            self.x = BORDER_THICKNESS

        # Pravá a logika dveří
        d_h = win_h // 4
        door_top = win_h // 2 - d_h // 2
        door_bottom = win_h // 2 + d_h // 2
        in_door_y = door_top < self.y < (door_bottom - self.size)

        if not (allow_exit and in_door_y):
            # Pokud nejsou dveře otevřené NEBO nejsme v jejich výšce, pravá zeď nás zastaví
            if self.x > win_w - BORDER_THICKNESS - self.size:
                self.x = win_w - BORDER_THICKNESS - self.size

            self.update_animation()

    def draw(self):
        # Blikání při zranění (zachováme tvou logiku)
        if self.inv_timer > 0 and (self.inv_timer // 5) % 2 == 0: return
        
        # Zrcadlení obrázku podle směru
        if self.facing_right:
            display_img = self.image
        else:
            # pygame.transform.flip(obrázek, horizontálně, vertikálně)
            display_img = pygame.transform.flip(self.image, True, False)
            
        # Vykreslení obrázku místo čtverečku
        SCREEN.blit(display_img, (int(self.x), int(self.y)))

class Enemy(Entity):
    def __init__(self, x, y, size, color, speed, hp=1):
        super().__init__(x, y, size, color, speed)
        self.hp = hp

    def follow(self, player):
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist != 0:
            new_x = self.x + (dx / dist) * self.speed
            new_y = self.y + (dy / dist) * self.speed
            
            # Zabráníme nepříteli vlézt do borderů
            self.x = max(BORDER_THICKNESS, min(WIDTH - BORDER_THICKNESS - self.size, new_x))
            self.y = max(BORDER_THICKNESS, min(HEIGHT - BORDER_THICKNESS - self.size, new_y))

class RangedEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 40, YELLOW, 2, hp=1)
        self.shoot_delay = 0
        self.range = 400

    def follow(self, player):
        dx, dy = player.x - self.x, player.y - self.y
        dist = math.hypot(dx, dy)
        if dist > self.range: super().follow(player)
        elif dist < self.range - 100:
            if dist != 0:
                self.x -= (dx / dist) * self.speed
                self.y -= (dy / dist) * self.speed
        
        self.shoot_delay += 1
        if self.shoot_delay >= 60:
            enemy_projectiles.append(Projectile(self.x + self.size/2, self.y + self.size/2, 
                                               player.x + player.size/2, player.y + player.size/2, 
                                               speed=6, color=YELLOW))
            self.shoot_delay = 0

class TankEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, 70, PURPLE, 1.2, hp=4)

class Projectile:
    def __init__(self, x, y, target_x, target_y, speed=12, size=6, color=WHITE):
        self.x, self.y = x, y
        self.size, self.color = size, color
        dx, dy = target_x - x, target_y - y
        dist = math.hypot(dx, dy)
        self.vel_x = (dx / dist) * speed if dist != 0 else 0
        self.vel_y = (dy / dist) * speed if dist != 0 else 0

    def move(self):
        self.x += self.vel_x
        self.y += self.vel_y

    def draw(self):
        pygame.draw.circle(SCREEN, self.color, (int(self.x), int(self.y)), self.size)

    def collides_with(self, entity):
        return pygame.Rect(entity.x, entity.y, entity.size, entity.size).collidepoint(self.x, self.y)

# --- UI Funkce ---
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
    # Definujeme bezpečné hranice (vnitřek arény)
    # Přidáváme malou rezervu (velikost nepřítele), aby se neobjevili přímo "přilepení" na zeď
    safe_min_x = BORDER_THICKNESS + 50
    safe_max_x = WIDTH - BORDER_THICKNESS - 100
    safe_min_y = BORDER_THICKNESS + 50
    safe_max_y = HEIGHT - BORDER_THICKNESS - 100

    # Náhodná pozice uvnitř herního pole
    x = random.randint(safe_min_x, safe_max_x)
    y = random.randint(safe_min_y, safe_max_y)
    
    # Kontrola, aby se nespawnovali přímo na hráči (v okruhu 300 pixelů)
    while math.hypot(x - player.x, y - player.y) < 300:
        x = random.randint(safe_min_x, safe_max_x)
        y = random.randint(safe_min_y, safe_max_y)

    # Náhodný výběr typu nepřítele
    etype = random.random()
    if etype < 0.6: 
        return Enemy(x, y, 50, RED, 3.5)
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
            # DŮLEŽITÉ: Musíme si uložit username pro pozdější odeslání času
            global user_name
            user_name = username 
            return True
        return False
    except:
        return False
    
def resolution_menu(screen):
    menu_running = True
    selected_res = None
    res_font = pygame.font.SysFont("Arial", 24) 
    
    button_width, button_height = 250, 50
    buttons = []
    # Výpočet dynamicky podle aktuálního (třeba i malého) okna
    curr_w, curr_h = screen.get_size()
    
    for i, res in enumerate(RESOLUTIONS):
        rect = pygame.Rect(
            curr_w // 2 - button_width // 2,
            150 + i * 80, # Trochu blíž k sobě
            button_width,
            button_height
        )
        buttons.append((rect, res))
    while menu_running:
        screen.fill((30, 30, 30)) # Tmavé pozadí
        
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

        # Vykreslení tlačítek
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
        # Tady je důležitá změna - vypíšeme si skutečnou odpověď serveru!
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

    # --- JEDINÝ ODBĚR UDÁLOSTÍ ---
    events = pygame.event.get() 
    for event in events:
        if event.type == pygame.QUIT: 
            running = False
  
       # --- STŘELBA ---
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not main_menu and not game_over and not paused:
                # Střílíme jen pokud máme náboje a nepřebíjíme
                if player.current_ammo > 0 and not player.is_reloading:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    projectiles.append(Projectile(player.x + player.size/2, player.y + player.size/2, mouse_x, mouse_y))
                    player.current_ammo -= 1
                    
                    # Automatické přebití po vystřílení
                    if player.current_ammo == 0:
                        player.reload()

        # --- PŘEBITÍ KLÁVESOU R ---
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                player.reload()

        # Globální ovládání ESC
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if not main_menu and not game_over:
                    paused = not paused
                    show_settings = False

        # --- LOGIKA PSANÍ PRO LOGIN (Zpracovává se pouze, když je aktivní login) ---
        if main_menu and show_login:
            if event.type == pygame.MOUSEBUTTONDOWN:
                # name_rect a pass_rect definujeme níže pro vykreslení, ale potřebujeme je i zde pro kolizi
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



    # 1. HLAVNÍ MENU (Včetně Login a Nastavení)
    if main_menu:
        if show_login:
            # --- OBRAZOVKA PŘIHLÁŠENÍ ---
            txt = title_font.render("PŘIHLÁŠENÍ", True, WHITE)
            SCREEN.blit(txt, (WIDTH//2 - txt.get_width()//2, 100))
            
            # Pole pro jméno
            name_label = font.render("Uživatelské jméno:", True, WHITE)
            SCREEN.blit(name_label, (WIDTH//2 - 150, 220))
            name_rect = pygame.Rect(WIDTH//2 - 150, 255, 300, 45)
            name_border_col = RED if active_field == "name" else BLACK
            pygame.draw.rect(SCREEN, name_border_col, name_rect, 2, border_radius=5)
            SCREEN.blit(font.render(user_name, True, WHITE), (name_rect.x + 10, name_rect.y + 7))

            # Pole pro heslo
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
                        # --- TADY JE TA ZMĚNA ---
                        chosen_res = resolution_menu(SCREEN) # Vyvoláme výběr
                        
                        # Nastavíme nové rozlišení
                        if chosen_res == (1920, 1080):
                            SCREEN = pygame.display.set_mode(chosen_res, pygame.FULLSCREEN)
                        else:
                            SCREEN = pygame.display.set_mode(chosen_res)
                        
                        # AKTUALIZACE PROMĚNNÝCH PRO CELOU HRU
                        WIDTH, HEIGHT = chosen_res 
                        
                        # RESET HRÁČE NA STŘED NOVÉHO OKNA
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
            # --- OBRAZOVKA NASTAVENÍ ---
            txt = title_font.render("OVLÁDÁNÍ", True, YELLOW)
            SCREEN.blit(txt, (WIDTH//2 - txt.get_width()//2, 150))
            controls = ["W,A,S,D - Pohyb", "LMB - Střelba", "ESC - Pauza", "---", "Jdi do dveří vpravo!"]
            for i, line in enumerate(controls):
                SCREEN.blit(font.render(line, True, WHITE), (WIDTH//2 - 100, 300 + i * 40))
            if draw_button("ZPĚT", WIDTH//2 - 100, HEIGHT - 150, 200, 60):
                show_settings = False
                pygame.time.delay(150)

        else:
            # --- ZÁKLADNÍ HLAVNÍ MENU ---
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

    elif in_starter_room:
        d_h = HEIGHT // 4  # Musí být stejné jako v player.move!
        door_open = (current_time - starter_timer) > 2000
        player.move(allow_exit=door_open)
        
        # Vykreslení zdí (používáme aktuální WIDTH a HEIGHT)
        pygame.draw.rect(SCREEN, WHITE, (0, 0, WIDTH, BORDER_THICKNESS)) # Horní
        pygame.draw.rect(SCREEN, WHITE, (0, HEIGHT - BORDER_THICKNESS, WIDTH, BORDER_THICKNESS)) # Spodní
        pygame.draw.rect(SCREEN, WHITE, (0, 0, BORDER_THICKNESS, HEIGHT)) # Levá
        
        if not door_open:
            # Plná pravá zeď
            pygame.draw.rect(SCREEN, WHITE, (WIDTH - BORDER_THICKNESS, 0, BORDER_THICKNESS, HEIGHT))
        else:
            # Pravá zeď s dírou pro dveře
            pygame.draw.rect(SCREEN, WHITE, (WIDTH - BORDER_THICKNESS, 0, BORDER_THICKNESS, HEIGHT // 2 - d_h // 2))
            pygame.draw.rect(SCREEN, WHITE, (WIDTH - BORDER_THICKNESS, HEIGHT // 2 + d_h // 2, BORDER_THICKNESS, HEIGHT))
            # Zelený indikátor dveří
            if (current_time // 250) % 2 == 0:
                pygame.draw.rect(SCREEN, GREEN, (WIDTH - BORDER_THICKNESS, HEIGHT // 2 - d_h // 2, BORDER_THICKNESS, d_h))

        player.draw()
        
        # Oprava detekce průchodu (aby odpovídala borderu)
        if player.x > WIDTH - BORDER_THICKNESS - player.size:
            in_starter_room = False
            game_start_time = current_time
            arena_start_time = pygame.time.get_ticks()
            player.x = BORDER_THICKNESS + 20 
            pygame.time.delay(100)

# 3. SAMOTNÁ HRA (ARÉNA)
    elif not game_over:
        if not paused:
            # Časovač
            elapsed_ms = current_time - arena_start_time
            seconds = elapsed_ms // 1000
            milis = elapsed_ms % 1000
            time_str = f"TIME: {seconds}:{milis:03d}"
            
            # --- POHYB HRÁČE ---
            player.move(allow_exit=room_cleared)

            # Přechod do další místnosti
            if room_cleared and player.x > WIDTH - BORDER_THICKNESS - player.size:
                if room_count < MAX_ROOMS:
                    room_cleared = False
                    total_spawned = 0
                    enemies = []
                    projectiles = []
                    enemy_projectiles = []
                    player.x = 80 
                    room_count += 1
                    MAX_ENEMIES += 6
                    spawn_cooldown = max(500, spawn_cooldown - 200)
                    arena_start_time = pygame.time.get_ticks()
                    pygame.time.delay(100)
                else:
                    send_time_to_django(user_name, elapsed_ms)
                    game_over = True
            
            # --- SPAWNOVÁNÍ ---
            if current_time - arena_start_time > 2000:
                if total_spawned < MAX_ENEMIES and current_time - last_spawn_time > spawn_cooldown:
                    enemies.append(spawn_enemy())
                    total_spawned += 1
                    last_spawn_time = current_time

            # --- LOGIKA PROJEKTILŮ A NEPŘÁTEL ---
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

            for ep in enemy_projectiles[:]:
                ep.move()
                if ep.collides_with(player): 
                    player.take_damage()
                    enemy_projectiles.remove(ep)
                elif not (0 <= ep.x <= WIDTH and 0 <= ep.y <= HEIGHT): 
                    enemy_projectiles.remove(ep)

            for e in enemies:
                e.follow(player)
                if player.get_rect().colliderect(e.get_rect()):
                    player.take_damage()
                    handle_collision(player, e, force=20)
                    
                    # --- FIX: Okamžitá kontrola hranic po odhození ---
                    curr_w, curr_h = SCREEN.get_size()
                    player.x = max(BORDER_THICKNESS, min(curr_w - BORDER_THICKNESS - player.size, player.x))
                    player.y = max(BORDER_THICKNESS, min(curr_h - BORDER_THICKNESS - player.size, player.y))
                        
            # Kolize mezi nepřáteli
            for i in range(len(enemies)):
                for j in range(i + 1, len(enemies)):
                    if enemies[i].get_rect().colliderect(enemies[j].get_rect()):
                        handle_collision(enemies[i], enemies[j], force=8)

            if player.hp <= 0: game_over = True
            player.update_reload()

        # --- VYKRESLOVÁNÍ ---
        # 1. Zdi (Tato část byla špatně odsazená)
        d_h = HEIGHT // 4

        pygame.draw.rect(SCREEN, RED, (0, 0, WIDTH, BORDER_THICKNESS)) 
        pygame.draw.rect(SCREEN, GREEN, (0, HEIGHT - BORDER_THICKNESS, WIDTH, BORDER_THICKNESS))
        pygame.draw.rect(SCREEN, YELLOW, (0, 0, BORDER_THICKNESS, HEIGHT)) 

        if not room_cleared:
            pygame.draw.rect(SCREEN, PURPLE, (WIDTH - BORDER_THICKNESS, 0, BORDER_THICKNESS, HEIGHT))
        else:
            pygame.draw.rect(SCREEN, PURPLE, (WIDTH - BORDER_THICKNESS, 0, BORDER_THICKNESS, HEIGHT // 2 - d_h // 2))
            pygame.draw.rect(SCREEN, PURPLE, (WIDTH - BORDER_THICKNESS, HEIGHT // 2 + d_h // 2, BORDER_THICKNESS, HEIGHT))
            if (pygame.time.get_ticks() // 250) % 2 == 0:
                pygame.draw.rect(SCREEN, GREEN, (WIDTH - BORDER_THICKNESS, HEIGHT // 2 - d_h // 2, BORDER_THICKNESS, d_h))


                
        # 2. Entity
        for p in projectiles: p.draw()
        for ep in enemy_projectiles: ep.draw()
        for e in enemies: e.draw()
        player.draw()
                # --- PEKELNÝ HUD (Pravý dolní roh) ---
        hud_width, hud_height = 280, 100
        hud_x = WIDTH - hud_width - 10
        hud_y = HEIGHT - hud_height - 10

        # Pozadí boxu (tmavě červený obdélník s černým okrajem)
        hud_rect = pygame.Rect(hud_x, hud_y, hud_width, hud_height)
        pygame.draw.rect(SCREEN, BLACK, hud_rect) # Podklad
        pygame.draw.rect(SCREEN, BLOOD_RED, hud_rect, 0, border_radius=8) # Výplň
        pygame.draw.rect(SCREEN, HELL_ORANGE, hud_rect, 3, border_radius=8) # Ohnivý okraj

        # Vykreslení životů (Srdíčka / Text)
        life_text = font.render(f"HP:", True, WHITE)
        SCREEN.blit(life_text, (hud_x + 15, hud_y + 15))
        
        # Grafické znázornění životů (červené čtverečky místo textu pro "pekelnější" vzhled)
        for i in range(3): # Max HP
            heart_rect = pygame.Rect(hud_x + 60 + (i * 35), hud_y + 18, 25, 25)
            if i < player.hp:
                pygame.draw.rect(SCREEN, RED, heart_rect, 0, border_radius=4) # Plný život
            else:
                pygame.draw.rect(SCREEN, GRAY, heart_rect, 2, border_radius=4) # Prázdný život

        # Vykreslení munice uvnitř boxu
        ammo_color = WHITE if not player.is_reloading else YELLOW
        ammo_label = "RELOADING..." if player.is_reloading else f"AMMO: {player.current_ammo}/{player.max_ammo}"
        ammo_render = font.render(ammo_label, True, ammo_color)
        SCREEN.blit(ammo_render, (hud_x + 15, hud_y + 55))

        # Malý indikátor přebíjení (progress bar) uvnitř HUDu
        if player.is_reloading:
            reload_bar_width = (player.reload_timer / player.reload_duration) * (hud_width - 30)
            pygame.draw.rect(SCREEN, YELLOW, (hud_x + 15, hud_y + 85, reload_bar_width, 5))


        SCREEN.blit(font.render(f"Místnost: {room_count} / {MAX_ROOMS}", True, YELLOW), (20, 50))
        

        time_render = font.render(time_str, True, WHITE)
        SCREEN.blit(time_render, (20, 140))


        dash_color = GREEN if player.dash_cooldown <= 0 else RED
        pygame.draw.rect(SCREEN, GRAY, (20, 140, 100, 10))
        if player.dash_cooldown > 0:
            # Ukazatel nabíjení
            charge_w = 100 - (player.dash_cooldown * 2) # Přizpůsob podle délky cooldownu
            pygame.draw.rect(SCREEN, dash_color, (20, 140, max(0, charge_w), 10))

        
    

        # Překryv při pauze
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
        
        # Kontrola, jestli hráč vyhrál (prošel 3 místnosti) nebo umřel
        if player.hp > 0:
            overlay.fill((0, 50, 0, 200)) # Průhledná zelená pro vítězství
            msg = "VICTORY!"
            color = (100, 255, 100)
        else:
            overlay.fill((50, 0, 0, 200)) # Průhledná červená pro smrt
            msg = "GAME OVER"
            color = WHITE
            
        SCREEN.blit(overlay, (0, 0))
        
        # Titulek (Victory / Game Over)
        txt = title_font.render(msg, True, color)
        SCREEN.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 100))
        
        # Finální čas
        final_time_str = f"Konečný čas: {elapsed_ms // 1000}:{elapsed_ms % 1000:03d}s"
        time_txt = font.render(final_time_str, True, WHITE)
        SCREEN.blit(time_txt, (WIDTH//2 - time_txt.get_width()//2, HEIGHT//2))

        # Tlačítko pro ukončení
        if draw_button("UKONČIT", WIDTH//2 - 100, HEIGHT//2 + 80, 200, 60): 
            running = False

    pygame.display.flip()
    CLOCK.tick(60)

pygame.quit()
sys.exit()