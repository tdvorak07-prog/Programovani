"""
Testy pro Speed Hell
Spustit: python -m pytest test_game.py -v
"""
import math
import pytest

# ---------------------------------------------------------------------------
# Stub pygame — testy nevyžadují grafické okno
# ---------------------------------------------------------------------------
import sys
from unittest.mock import MagicMock, patch

# Celý pygame mockujeme před importem main
pygame_mock = MagicMock()
pygame_mock.Rect = __import__("pygame").Rect if "pygame" in sys.modules else None

# Jednoduchý náhradní Rect který nepotřebuje pygame display
class FakeRect:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.width, self.height = x, y, w, h

    @property
    def left(self):   return self.x
    @property
    def right(self):  return self.x + self.width
    @property
    def top(self):    return self.y
    @property
    def bottom(self): return self.y + self.height
    @property
    def centerx(self): return self.x + self.width // 2
    @property
    def centery(self): return self.y + self.height // 2
    @property
    def center(self): return (self.centerx, self.centery)

    @left.setter
    def left(self, v):   self.x = v
    @right.setter
    def right(self, v):  self.x = v - self.width
    @top.setter
    def top(self, v):    self.y = v
    @bottom.setter
    def bottom(self, v): self.y = v - self.height

    def colliderect(self, other):
        return (self.x < other.x + other.width  and
                self.x + self.width  > other.x  and
                self.y < other.y + other.height and
                self.y + self.height > other.y)

    def __repr__(self):
        return f"FakeRect({self.x}, {self.y}, {self.width}, {self.height})"


# ---------------------------------------------------------------------------
# Jednoduché datové třídy — kopie logiky z main.py, bez pygame závislostí
# ---------------------------------------------------------------------------

BORDER_THICKNESS = 60
WIDTH, HEIGHT = 1920, 1080

class SimplePlayer:
    """Odlehčená verze Player pro testování pohybu a kolizí."""
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.speed = 6
        self.hp = 3
        self.is_dead = False
        self.inv_timer = 0
        self.rect = FakeRect(x, y, 40, 70)

    def apply_boundary(self, win_w=WIDTH, win_h=HEIGHT):
        """Stejná hranicová logika jako v main.py."""
        if self.rect.top < BORDER_THICKNESS:
            self.rect.top = BORDER_THICKNESS
            self.y = float(self.rect.y)
        if self.rect.bottom > win_h - BORDER_THICKNESS:
            self.rect.bottom = win_h - BORDER_THICKNESS
            self.y = float(self.rect.y)
        if self.rect.left < BORDER_THICKNESS:
            self.rect.left = BORDER_THICKNESS
            self.x = float(self.rect.x)
        if self.rect.right > win_w - BORDER_THICKNESS:
            self.rect.right = win_w - BORDER_THICKNESS
            self.x = float(self.rect.x)

    def take_damage(self):
        if self.inv_timer == 0 and not self.is_dead:
            self.hp -= 1
            if self.hp <= 0:
                self.hp = 0
                self.is_dead = True
            else:
                self.inv_timer = 60

    def sync_rect(self):
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)


class SimpleEnemy:
    def __init__(self, x, y, size=50):
        self.x = float(x)
        self.y = float(y)
        self.size = size
        self.rect = FakeRect(x, y, size, size)


def handle_collision(obj1, obj2, force=10):
    dx = obj1.x - obj2.x
    dy = obj1.y - obj2.y
    dist = math.hypot(dx, dy)
    if dist < (obj1.size / 2 + obj2.size / 2) if hasattr(obj1, "size") else True:
        if dist == 0:
            dist = 0.1
        push_x = (dx / dist) * force
        push_y = (dy / dist) * force
        obj1.x += push_x
        obj1.y += push_y
        obj2.x -= push_x
        obj2.y -= push_y


# ===========================================================================
# TESTY — Herní stav
# ===========================================================================

class TestGameState:

    def test_room_cleared_when_all_enemies_dead(self):
        """room_cleared se nastaví pokud total_spawned >= MAX_ENEMIES a enemies == []."""
        MAX_ENEMIES = 5
        total_spawned = 5
        enemies = []
        room_cleared = total_spawned >= MAX_ENEMIES and len(enemies) == 0
        assert room_cleared is True

    def test_room_not_cleared_when_enemies_remain(self):
        enemies = [SimpleEnemy(100, 100)]
        total_spawned = 5
        MAX_ENEMIES = 5
        room_cleared = total_spawned >= MAX_ENEMIES and len(enemies) == 0
        assert room_cleared is False

    def test_room_not_cleared_when_not_all_spawned(self):
        enemies = []
        total_spawned = 3
        MAX_ENEMIES = 5
        room_cleared = total_spawned >= MAX_ENEMIES and len(enemies) == 0
        assert room_cleared is False

    def test_game_over_on_player_death(self):
        player = SimplePlayer(500, 500)
        player.hp = 0
        player.is_dead = True
        player.death_timer = 0
        game_over = player.is_dead and player.death_timer <= 0
        assert game_over is True

    def test_game_not_over_during_death_animation(self):
        player = SimplePlayer(500, 500)
        player.is_dead = True
        player.death_timer = 150  # animace stále běží
        game_over = player.is_dead and player.death_timer <= 0
        assert game_over is False

    def test_timer_accumulates_across_rooms(self):
        accumulated_time = 5000   # ms z předchozí místnosti
        arena_start_time = 1000
        current_time = 4000
        total_elapsed = accumulated_time + (current_time - arena_start_time)
        assert total_elapsed == 8000

    def test_timer_formats_correctly(self):
        total_elapsed_ms = 65432
        seconds = total_elapsed_ms // 1000
        milis = total_elapsed_ms % 1000
        time_str = f"TIME: {seconds}:{milis:03d}"
        assert time_str == "TIME: 65:432"

    def test_max_enemies_increases_per_room(self):
        MAX_ENEMIES = 15
        for _ in range(3):
            MAX_ENEMIES += 6
        assert MAX_ENEMIES == 33

    def test_spawn_cooldown_decreases_per_room(self):
        spawn_cooldown = 1500
        for _ in range(3):
            spawn_cooldown = max(500, spawn_cooldown - 200)
        assert spawn_cooldown == 900

    def test_spawn_cooldown_minimum(self):
        spawn_cooldown = 600
        for _ in range(10):
            spawn_cooldown = max(500, spawn_cooldown - 200)
        assert spawn_cooldown == 500


# ===========================================================================
# TESTY — Pohyb a kolize hráče
# ===========================================================================

class TestPlayerMovement:

    def test_player_clamped_to_top_border(self):
        player = SimplePlayer(500, 10)  # příliš vysoko
        player.rect.y = 10
        player.apply_boundary()
        assert player.rect.top >= BORDER_THICKNESS

    def test_player_clamped_to_bottom_border(self):
        player = SimplePlayer(500, HEIGHT - 20)
        player.rect.y = HEIGHT - 20
        player.apply_boundary()
        assert player.rect.bottom <= HEIGHT - BORDER_THICKNESS

    def test_player_clamped_to_left_border(self):
        player = SimplePlayer(5, 300)
        player.rect.x = 5
        player.apply_boundary()
        assert player.rect.left >= BORDER_THICKNESS

    def test_player_clamped_to_right_border(self):
        player = SimplePlayer(WIDTH - 10, 300)
        player.rect.x = WIDTH - 10
        player.apply_boundary()
        assert player.rect.right <= WIDTH - BORDER_THICKNESS

    def test_player_stays_in_valid_area(self):
        player = SimplePlayer(500, 400)
        player.apply_boundary()
        assert player.rect.left >= BORDER_THICKNESS
        assert player.rect.right <= WIDTH - BORDER_THICKNESS
        assert player.rect.top >= BORDER_THICKNESS
        assert player.rect.bottom <= HEIGHT - BORDER_THICKNESS


class TestPlayerDamage:

    def test_take_damage_reduces_hp(self):
        player = SimplePlayer(500, 400)
        player.take_damage()
        assert player.hp == 2

    def test_take_damage_sets_invincibility(self):
        player = SimplePlayer(500, 400)
        player.take_damage()
        assert player.inv_timer == 60

    def test_no_damage_during_invincibility(self):
        player = SimplePlayer(500, 400)
        player.inv_timer = 30
        player.take_damage()
        assert player.hp == 3  # HP se nezměnilo

    def test_death_at_zero_hp(self):
        player = SimplePlayer(500, 400)
        player.hp = 1
        player.take_damage()
        assert player.is_dead is True
        assert player.hp == 0

    def test_hp_does_not_go_negative(self):
        player = SimplePlayer(500, 400)
        player.hp = 1
        player.take_damage()
        assert player.hp >= 0


class TestCollision:

    def test_player_enemy_collision_detected(self):
        player = SimplePlayer(100, 100)
        enemy = SimpleEnemy(110, 110)
        assert player.rect.colliderect(enemy.rect) is True

    def test_player_enemy_no_collision(self):
        player = SimplePlayer(100, 100)
        enemy = SimpleEnemy(500, 500)
        assert player.rect.colliderect(enemy.rect) is False

    def test_collision_push_separates_objects(self):
        """Po kolizi se objekty od sebe oddálí."""
        class Obj:
            def __init__(self, x, y, size):
                self.x, self.y, self.size = float(x), float(y), size

        a = Obj(100, 100, 40)
        b = Obj(110, 100, 40)
        dist_before = math.hypot(a.x - b.x, a.y - b.y)
        handle_collision(a, b, force=10)
        dist_after = math.hypot(a.x - b.x, a.y - b.y)
        assert dist_after > dist_before


# ===========================================================================
# TESTY — AoE logika
# ===========================================================================

class TestAoE:

    def test_aoe_kills_max_5_enemies(self):
        player = SimplePlayer(500, 500)
        player.aoe_radius = 250
        enemies = [SimpleEnemy(510 + i * 5, 510) for i in range(10)]

        killed = 0
        remaining = []
        for e in enemies[:]:
            dist = math.hypot(e.x - player.x, e.y - player.y)
            if dist <= player.aoe_radius:
                killed += 1
                if killed >= 5:
                    remaining = enemies[enemies.index(e) + 1:]
                    break
            else:
                remaining.append(e)

        assert killed == 5

    def test_aoe_does_not_kill_out_of_range(self):
        player = SimplePlayer(500, 500)
        player.aoe_radius = 100
        enemies = [SimpleEnemy(900, 900)]  # daleko mimo dosah

        killed = 0
        for e in enemies:
            dist = math.hypot(e.x - player.x, e.y - player.y)
            if dist <= player.aoe_radius:
                killed += 1

        assert killed == 0

    def test_aoe_cooldown_enforced(self):
        last_aoe_time = 0
        current_time = 5000
        cooldown = 10000
        can_use = (current_time - last_aoe_time) >= cooldown
        assert can_use is False

    def test_aoe_ready_after_cooldown(self):
        last_aoe_time = 0
        current_time = 10001
        cooldown = 10000
        can_use = (current_time - last_aoe_time) >= cooldown
        assert can_use is True
