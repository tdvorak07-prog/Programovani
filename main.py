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
RESOLUTIONS = [
    (1920, 1080),
    (1600, 900), 
    (800, 600)
]

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
MAX_ENEMIES = 8
player_shoot_cooldown = 1
score = 0
total_spawned = 0
arena_start_time = 0
elapsed_ms = 0
game_start_time = 0      # Čas pro spawn nepřátel v hlavní hře
starter_timer = 0        # Čas pro otevření dveří v první místnosti

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

    def take_damage(self):
        if self.inv_timer <= 0:
            self.hp -= 1
            self.inv_timer = 60
            return True
        return False

    def move(self, allow_exit=False):
        if self.inv_timer > 0: self.inv_timer -= 1
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_s]: dy += 1
        if keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_d]: dx += 1
        
        if dx != 0 or dy != 0:
            length = math.hypot(dx, dy)
            new_x = self.x + (dx / length) * self.speed
            new_y = self.y + (dy / length) * self.speed
            
            # --- LOGIKA KOLIZÍ SE ZDMI ---
            
            # Horní, spodní a levá hranice jsou pevné
            new_y = max(BORDER_THICKNESS, min(HEIGHT - BORDER_THICKNESS - self.size, new_y))
            new_x = max(BORDER_THICKNESS, new_x)

            # Pravá strana (Dveře)
            d_h = 200
            door_top = HEIGHT // 2 - d_h // 2
            door_bottom = HEIGHT // 2 + d_h // 2
            
            # Pokud se hráč snaží jet za pravý okraj
            if new_x > WIDTH - BORDER_THICKNESS - self.size:
                # Jsou dveře otevřené A hráč je trefil (je v jejich rozmezí Y)?
                if allow_exit and door_top < self.y < (door_bottom - self.size):
                    # Povolíme mu projít (necháme new_x být)
                    pass
                else:
                    # Jinak ho zastavíme o zeď
                    new_x = WIDTH - BORDER_THICKNESS - self.size

            self.x = new_x
            self.y = new_y

    def draw(self):
        if self.inv_timer > 0 and (self.inv_timer // 5) % 2 == 0: return
        super().draw()

class Enemy(Entity):
    def __init__(self, x, y, size, color, speed, hp=1):
        super().__init__(x, y, size, color, speed)
        self.hp = hp

    def follow(self, player):
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy)
        if dist != 0:
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed

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
    side = random.choice(['top', 'bottom', 'left', 'right'])
    if side == 'top': x, y = random.randint(0, WIDTH), -70
    elif side == 'bottom': x, y = random.randint(0, WIDTH), HEIGHT + 70
    elif side == 'left': x, y = -70, random.randint(0, HEIGHT)
    else: x, y = WIDTH + 70, random.randint(0, HEIGHT)
    
    etype = random.random()
    if etype < 0.6: return Enemy(x, y, 50, RED, 3.5)
    elif etype < 0.85: return RangedEnemy(x, y)
    else: return TankEnemy(x, y)

def verify_login_with_django(username, password):
    url = "http://127.0.0.1:8000/api/login/"
    payload = {"username": username, "password": password}
    try:
        response = requests.post(url, json=payload, timeout=5)
        print(f"Server odpověděl kódem: {response.status_code}") # Tohle ti napoví
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("CHYBA: Django server neběží! (Connection Refused)")
        return False
    except Exception as e:
        print(f"Jiná chyba při spojení: {e}")
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
    url = "http://127.0.0.1:8000/api/update_playtime/" # Adresa tvého nového view
    payload = {"username": username, "play_time": time_ms}
    try:
        requests.post(url, json=payload, timeout=3)
        print(f"Čas {time_ms}ms uložen pro {username}")
    except:
        print("Nepodařilo se spojit se serverem pro uložení času.")


# --- Hlavní smyčka ---
running = True
while running:
    current_time = pygame.time.get_ticks()

    # --- JEDINÝ ODBĚR UDÁLOSTÍ ---
    events = pygame.event.get() 
    for event in events:
        if event.type == pygame.QUIT: 
            running = False
        
        # Globální ovládání ESC
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
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

    # 2. STARTOVACÍ MÍSTNOST
    elif in_starter_room:
        door_open = (current_time - starter_timer) > 2000
        player.move(allow_exit=door_open)
        
        # Zdi startovací místnosti
        pygame.draw.rect(SCREEN, WHITE, (0, 0, WIDTH, BORDER_THICKNESS)) 
        pygame.draw.rect(SCREEN, WHITE, (0, HEIGHT - BORDER_THICKNESS, WIDTH, BORDER_THICKNESS))
        pygame.draw.rect(SCREEN, WHITE, (0, 0, BORDER_THICKNESS, HEIGHT))
        
        if not door_open:
            pygame.draw.rect(SCREEN, WHITE, (WIDTH - BORDER_THICKNESS, 0, BORDER_THICKNESS, HEIGHT))
        else:
            d_h = 200
            pygame.draw.rect(SCREEN, WHITE, (WIDTH - BORDER_THICKNESS, 0, BORDER_THICKNESS, HEIGHT//2 - d_h//2))
            pygame.draw.rect(SCREEN, WHITE, (WIDTH - BORDER_THICKNESS, HEIGHT//2 + d_h//2, BORDER_THICKNESS, HEIGHT))
            if (current_time // 250) % 2 == 0:
                pygame.draw.rect(SCREEN, GREEN, (WIDTH - BORDER_THICKNESS, HEIGHT//2 - d_h//2, BORDER_THICKNESS, d_h))

        player.draw()
        
        if player.x > WIDTH - player.size:
            in_starter_room = False
            game_start_time = current_time
            arena_start_time = pygame.time.get_ticks() # Resetujeme čas pro milisekundy
            player.x = 50 
            pygame.time.delay(100)

    # 3. SAMOTNÁ HRA (ARÉNA)
    elif not game_over:
       
        # Pauza je speciální stav uvnitř běhu hry
        if not paused:
            elapsed_ms = current_time - arena_start_time
            seconds = elapsed_ms // 1000
            milis = elapsed_ms % 1000
            time_str = f"TIME: {seconds}:{milis:03d}"
            player.move()
            
            if current_time - game_start_time > 5000:
                if len(enemies) < MAX_ENEMIES and total_spawned < MAX_ENEMIES:
                    enemies.append(spawn_enemy())
                    total_spawned += 1

            if pygame.mouse.get_pressed()[0] and player_shoot_cooldown <= 0:
                mx, my = pygame.mouse.get_pos()
                projectiles.append(Projectile(player.x + player.size/2, player.y + player.size/2, mx, my))
                player_shoot_cooldown = 12
            if player_shoot_cooldown > 0: player_shoot_cooldown -= 1

            # Logika střel a nepřátel
            for p in projectiles[:]:
                p.move()
                if not (0 <= p.x <= WIDTH and 0 <= p.y <= HEIGHT): projectiles.remove(p)
                else:
                   for e in enemies[:]:
                        if p.collides_with(e):
                            e.hp -= 1
                            if p in projectiles: projectiles.remove(p)
                            if e.hp <= 0: 
                                enemies.remove(e)
                                score += 100
                                
                                if total_spawned >= MAX_ENEMIES and len(enemies) == 0:
                                    print("Aréna vyčištěna!")
                                    send_time_to_django(user_name, elapsed_ms)
                                    game_over = True
                            break

            for ep in enemy_projectiles[:]:
                ep.move()
                if ep.collides_with(player): player.take_damage(); enemy_projectiles.remove(ep)
                elif not (0 <= ep.x <= WIDTH and 0 <= ep.y <= HEIGHT): enemy_projectiles.remove(ep)

            for e in enemies:
                e.follow(player)
                if player.get_rect().colliderect(e.get_rect()):
                    player.take_damage()
                    handle_collision(player, e, force=20)
            
            for i in range(len(enemies)):
                for j in range(i + 1, len(enemies)):
                    if enemies[i].get_rect().colliderect(enemies[j].get_rect()):
                        handle_collision(enemies[i], enemies[j], force=8)

            if player.hp <= 0: game_over = True

        # Vykreslování arény (i při pauze, aby byla vidět na pozadí)
        pygame.draw.rect(SCREEN, RED, (0, 0, WIDTH, BORDER_THICKNESS))
        pygame.draw.rect(SCREEN, GREEN, (0, HEIGHT - BORDER_THICKNESS, WIDTH, BORDER_THICKNESS))
        pygame.draw.rect(SCREEN, YELLOW, (0, 0, BORDER_THICKNESS, HEIGHT))
        pygame.draw.rect(SCREEN, PURPLE, (WIDTH - BORDER_THICKNESS, 0, BORDER_THICKNESS, HEIGHT))
        
        for p in projectiles: p.draw()
        for ep in enemy_projectiles: ep.draw()
        for e in enemies: e.draw()
        player.draw()
        
        SCREEN.blit(font.render(f"Hráč: {user_name}", True, WHITE), (20, 20))
        SCREEN.blit(font.render(f"SCORE: {score}", True, WHITE), (20, 50))
        SCREEN.blit(font.render(f"LIFE: {'♥' * player.hp}", True, RED), (20, 80))
        time_render = font.render(time_str, True, WHITE)
        SCREEN.blit(time_render, (20, 110))

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
        overlay.fill((50, 0, 0, 180))
        SCREEN.blit(overlay, (0, 0))
        txt = title_font.render("GAME OVER", True, WHITE)
        SCREEN.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 50))
        if draw_button("UKONČIT", WIDTH//2 - 100, HEIGHT//2 + 50, 200, 60): running = False

    pygame.display.flip()
    CLOCK.tick(60)

pygame.quit()
sys.exit()