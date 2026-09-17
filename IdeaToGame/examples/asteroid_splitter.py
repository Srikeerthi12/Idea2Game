"""
ASTEROID SPLITTER
-----------------
Rotate, shoot, split, survive — a game where every victory makes the field more dangerous.

Controls:
    Left / A  : rotate counter-clockwise
    Right / D : rotate clockwise
    Space     : fire
    P         : pause
    R         : restart (on game over)
    Esc       : quit

Single-file Pygame. No external assets.
"""

import sys
import math
import random

import pygame

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WIDTH, HEIGHT = 960, 640
FPS = 60

BG_COLOR = (10, 10, 20)
SHIP_COLOR = (80, 220, 255)
BULLET_COLOR = (255, 255, 255)
TEXT_COLOR = (230, 230, 240)
DIM_TEXT = (140, 140, 160)

ASTEROID_COLORS = {
    "large": (140, 140, 150),
    "medium": (180, 150, 110),
    "small": (220, 140, 80),
}

# Player tuning
SHIP_RADIUS = 14
SHIP_ROT_SPEED = math.radians(220)   # rad/s
SHIP_START_SPEED = 90.0              # px/s
SHIP_MAX_SPEED = 200.0               # px/s
SHIP_SPEED_RAMP = 8.0                # px/s per 20s tick
FIRE_COOLDOWN = 0.18                 # s

# Bullet tuning
BULLET_SPEED = 520.0
BULLET_LIFETIME = 1.1
BULLET_RADIUS = 3

# Asteroid tiers
ASTEROID_TIERS = {
    "large":  {"radius": 40, "speed": (40, 70),   "points": 20,  "splits": "medium"},
    "medium": {"radius": 22, "speed": (70, 110),  "points": 50,  "splits": "small"},
    "small":  {"radius": 11, "speed": (110, 160), "points": 100, "splits": None},
}

# Difficulty
DIFFICULTY_INTERVAL = 20.0           # seconds
SPAWN_RATE_BASE = 1.6                # seconds between spawns
SPAWN_RATE_MIN = 0.45
SPAWN_RATE_STEP = 0.85               # multiplier per difficulty tick

# Combo
COMBO_WINDOW = 1.5
COMBO_THRESHOLD = 3
COMBO_MULTIPLIER = 2

HIGHSCORE_FILE = "highscore.txt"


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def wrap_pos(x, y):
    return x % WIDTH, y % HEIGHT


def wrap_delta(dx, dy):
    """Shortest delta between two points on a wrapping torus."""
    if dx > WIDTH / 2:
        dx -= WIDTH
    elif dx < -WIDTH / 2:
        dx += WIDTH
    if dy > HEIGHT / 2:
        dy -= HEIGHT
    elif dy < -HEIGHT / 2:
        dy += HEIGHT
    return dx, dy


def load_highscore():
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            return int(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def save_highscore(score):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(int(score)))
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

class Ship:
    def __init__(self):
        self.x = WIDTH / 2
        self.y = HEIGHT / 2
        self.angle = -math.pi / 2  # pointing up
        self.speed = SHIP_START_SPEED
        self.fire_timer = 0.0
        self.trail = []  # list of [x, y, life]

    def update(self, dt, keys):
        # Rotation
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.angle -= SHIP_ROT_SPEED * dt
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.angle += SHIP_ROT_SPEED * dt

        # Constant forward drift
        self.x += math.cos(self.angle) * self.speed * dt
        self.y += math.sin(self.angle) * self.speed * dt
        self.x, self.y = wrap_pos(self.x, self.y)

        # Fire cooldown
        if self.fire_timer > 0:
            self.fire_timer -= dt

        # Trail
        self.trail.append([self.x, self.y, 0.35])
        for t in self.trail:
            t[2] -= dt
        self.trail = [t for t in self.trail if t[2] > 0]

    def can_fire(self):
        return self.fire_timer <= 0

    def fire(self):
        self.fire_timer = FIRE_COOLDOWN
        nose_x = self.x + math.cos(self.angle) * SHIP_RADIUS
        nose_y = self.y + math.sin(self.angle) * SHIP_RADIUS
        return Bullet(nose_x, nose_y, self.angle)

    def nose(self):
        return (self.x + math.cos(self.angle) * SHIP_RADIUS,
                self.y + math.sin(self.angle) * SHIP_RADIUS)

    def draw(self, surf):
        # Trail
        for tx, ty, life in self.trail:
            alpha = max(0, min(255, int(120 * (life / 0.35))))
            r = max(1, int(3 * (life / 0.35)))
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (80, 220, 255, alpha), (r, r), r)
            surf.blit(s, (tx - r, ty - r))

        # Triangle
        pts = []
        for a_off, r in ((0, SHIP_RADIUS),
                         (math.radians(140), SHIP_RADIUS * 0.85),
                         (math.radians(-140), SHIP_RADIUS * 0.85)):
            a = self.angle + a_off
            pts.append((self.x + math.cos(a) * r,
                        self.y + math.sin(a) * r))
        pygame.draw.polygon(surf, SHIP_COLOR, pts, 2)
        # Cockpit dot
        pygame.draw.circle(surf, SHIP_COLOR, (int(self.x), int(self.y)), 2)


class Bullet:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * BULLET_SPEED
        self.vy = math.sin(angle) * BULLET_SPEED
        self.life = BULLET_LIFETIME

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x, self.y = wrap_pos(self.x, self.y)
        self.life -= dt

    def alive(self):
        return self.life > 0

    def draw(self, surf):
        pygame.draw.circle(surf, BULLET_COLOR,
                           (int(self.x), int(self.y)), BULLET_RADIUS)


class Asteroid:
    def __init__(self, x, y, tier, vx=None, vy=None):
        self.x = x
        self.y = y
        self.tier = tier
        cfg = ASTEROID_TIERS[tier]
        self.radius = cfg["radius"]
        self.points = cfg["points"]

        if vx is None or vy is None:
            speed = random.uniform(*cfg["speed"])
            ang = random.uniform(0, math.tau)
            self.vx = math.cos(ang) * speed
            self.vy = math.sin(ang) * speed
        else:
            self.vx = vx
            self.vy = vy

        # Irregular polygon
        n = random.randint(8, 12)
        self.verts = []
        for i in range(n):
            a = (i / n) * math.tau
            r = self.radius * random.uniform(0.72, 1.15)
            self.verts.append((a, r))

        self.rot = random.uniform(0, math.tau)
        self.rot_speed = random.uniform(-1.2, 1.2)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x, self.y = wrap_pos(self.x, self.y)
        self.rot += self.rot_speed * dt

    def draw(self, surf):
        color = ASTEROID_COLORS[self.tier]
        pts = []
        for a, r in self.verts:
            ang = a + self.rot
            pts.append((self.x + math.cos(ang) * r,
                        self.y + math.sin(ang) * r))
        pygame.draw.polygon(surf, color, pts, 2)

    def split(self):
        """Return list of child asteroids."""
        cfg = ASTEROID_TIERS[self.tier]
        child_tier = cfg["splits"]
        if child_tier is None:
            return []
        children = []
        base_ang = math.atan2(self.vy, self.vx)
        for sign in (-1, 1):
            offset = math.radians(random.uniform(30, 60)) * sign
            ang = base_ang + offset
            speed = random.uniform(*ASTEROID_TIERS[child_tier]["speed"])
            children.append(Asteroid(
                self.x, self.y, child_tier,
                vx=math.cos(ang) * speed,
                vy=math.sin(ang) * speed,
            ))
        return children


class Particle:
    def __init__(self, x, y, color):
        ang = random.uniform(0, math.tau)
        speed = random.uniform(40, 180)
        self.x = x
        self.y = y
        self.vx = math.cos(ang) * speed
        self.vy = math.sin(ang) * speed
        self.life = random.uniform(0.3, 0.7)
        self.max_life = self.life
        self.color = color

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x, self.y = wrap_pos(self.x, self.y)
        self.life -= dt

    def alive(self):
        return self.life > 0

    def draw(self, surf):
        alpha = max(0, min(255, int(255 * (self.life / self.max_life))))
        r = 2
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r, r), r)
        surf.blit(s, (self.x - r, self.y - r))


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------

class Game:
    def __init__(self, screen):
        self.screen = screen
        self.font_big = pygame.font.SysFont("consolas,couriernew,monospace", 48, bold=True)
        self.font_med = pygame.font.SysFont("consolas,couriernew,monospace", 26, bold=True)
        self.font_small = pygame.font.SysFont("consolas,couriernew,monospace", 18)
        self.highscore = load_highscore()
        self.reset()

    def reset(self):
        self.ship = Ship()
        self.bullets = []
        self.asteroids = []
        self.particles = []
        self.score = 0
        self.survival_time = 0.0
        self.spawn_timer = 1.0
        self.difficulty_timer = 0.0
        self.difficulty_level = 0
        self.spawn_interval = SPAWN_RATE_BASE
        self.shake = 0.0
        self.paused = False
        self.game_over = False
        self.combo_count = 0
        self.combo_timer = 0.0
        self.combo_active = False
        self.muzzle_flash = 0.0

        # Seed a few asteroids
        for _ in range(4):
            self.spawn_asteroid()

    # -- spawning -----------------------------------------------------------

    def spawn_asteroid(self):
        # Spawn off-screen edge
        edge = random.randint(0, 3)
        if edge == 0:      # top
            x = random.uniform(0, WIDTH)
            y = -60
        elif edge == 1:    # bottom
            x = random.uniform(0, WIDTH)
            y = HEIGHT + 60
        elif edge == 2:    # left
            x = -60
            y = random.uniform(0, HEIGHT)
        else:              # right
            x = WIDTH + 60
            y = random.uniform(0, HEIGHT)

        # Higher difficulty -> bias toward medium asteroids
        if self.difficulty_level >= 3 and random.random() < 0.35:
            tier = "medium"
        else:
            tier = "large"
        self.asteroids.append(Asteroid(x, y, tier))

    # -- events -------------------------------------------------------------

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "quit"
            if event.key == pygame.K_p and not self.game_over:
                self.paused = not self.paused
            if event.key == pygame.K_r and self.game_over:
                self.reset()
            if event.key == pygame.K_SPACE and not self.paused and not self.game_over:
                if self.ship.can_fire():
                    self.bullets.append(self.ship.fire())
                    self.muzzle_flash = 0.06
        return None

    # -- update -------------------------------------------------------------

    def update(self, dt):
        if self.paused or self.game_over:
            return

        self.survival_time += dt
        self.score += dt  # +1 per second survival

        # Difficulty ramp
        self.difficulty_timer += dt
        if self.difficulty_timer >= DIFFICULTY_INTERVAL:
            self.difficulty_timer -= DIFFICULTY_INTERVAL
            self.difficulty_level += 1
            self.spawn_interval = max(
                SPAWN_RATE_MIN,
                self.spawn_interval * SPAWN_RATE_STEP,
            )
            self.ship.speed = min(SHIP_MAX_SPEED,
                                  self.ship.speed + SHIP_SPEED_RAMP)

        # Ship
        keys = pygame.key.get_pressed()
        self.ship.update(dt, keys)

        # Muzzle flash
        if self.muzzle_flash > 0:
            self.muzzle_flash -= dt

        # Bullets
        for b in self.bullets:
            b.update(dt)
        self.bullets = [b for b in self.bullets if b.alive()]

        # Asteroids
        for a in self.asteroids:
            a.update(dt)

        # Spawn
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_asteroid()
            self.spawn_timer = self.spawn_interval * random.uniform(0.8, 1.2)

        # Particles
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive()]

        # Combo timer
        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo_count = 0
                self.combo_active = False

        # Screen shake decay
        if self.shake > 0:
            self.shake = max(0, self.shake - dt * 30)

        # Collisions: bullets vs asteroids
        self._bullet_asteroid_collisions()

        # Collisions: ship vs asteroids
        self._ship_asteroid_collisions()

    def _bullet_asteroid_collisions(self):
        # Iterate bullets; for each, find first asteroid hit and destroy it.
        # Rebuild lists safely to avoid index invalidation.
        surviving_bullets = []
        for b in self.bullets:
            hit_index = -1
            for ai, a in enumerate(self.asteroids):
                dx, dy = wrap_delta(a.x - b.x, a.y - b.y)
                if dx * dx + dy * dy <= (a.radius + BULLET_RADIUS) ** 2:
                    hit_index = ai
                    break
            if hit_index >= 0:
                self._destroy_asteroid(hit_index)
            else:
                surviving_bullets.append(b)
        self.bullets = surviving_bullets

    def _destroy_asteroid(self, index):
        a = self.asteroids.pop(index)
        # Score
        base = a.points
        # Combo
        self.combo_count += 1
        self.combo_timer = COMBO_WINDOW
        if self.combo_count >= COMBO_THRESHOLD:
            self.combo_active = True
        mult = COMBO_MULTIPLIER if self.combo_active else 1
        self.score += base * mult

        # Particles
        color = ASTEROID_COLORS[a.tier]
        for _ in range(random.randint(6, 10)):
            self.particles.append(Particle(a.x, a.y, color))

        # Screen shake
        self.shake = min(6.0, self.shake + 3.0)

        # Split
        for child in a.split():
            self.asteroids.append(child)

    def _ship_asteroid_collisions(self):
        for a in self.asteroids:
            dx, dy = wrap_delta(a.x - self.ship.x, a.y - self.ship.y)
            if dx * dx + dy * dy <= (a.radius + SHIP_RADIUS * 0.7) ** 2:
                self._game_over()
                return

    def _game_over(self):
        self.game_over = True
        # Death particles
        for _ in range(24):
            self.particles.append(Particle(self.ship.x, self.ship.y, SHIP_COLOR))
        self.shake = 8.0
        if self.score > self.highscore:
            self.highscore = int(self.score)
            save_highscore(self.highscore)

    # -- draw ---------------------------------------------------------------

    def draw(self):
        # Shake offset
        ox = oy = 0
        if self.shake > 0:
            ox = random.uniform(-self.shake, self.shake)
            oy = random.uniform(-self.shake, self.shake)

        # Render to a temp surface for shake
        surf = pygame.Surface((WIDTH, HEIGHT))
        surf.fill(BG_COLOR)

        # Starfield-ish subtle dots (static, cheap)
        for i in range(60):
            sx = (i * 137) % WIDTH
            sy = (i * 251) % HEIGHT
            pygame.draw.circle(surf, (30, 30, 50), (sx, sy), 1)

        # Asteroids
        for a in self.asteroids:
            a.draw(surf)

        # Bullets
        for b in self.bullets:
            b.draw(surf)

        # Particles
        for p in self.particles:
            p.draw(surf)

        # Ship
        if not self.game_over:
            self.ship.draw(surf)
            # Muzzle flash
            if self.muzzle_flash > 0:
                nx, ny = self.ship.nose()
                pygame.draw.circle(surf, (255, 255, 255), (int(nx), int(ny)), 5)

        # HUD
        self._draw_hud(surf)

        if self.paused:
            self._draw_center_text(surf, "PAUSED", "Press P to resume")

        if self.game_over:
            self._draw_game_over(surf)

        # Blit with shake
        self.screen.fill(BG_COLOR)
        self.screen.blit(surf, (ox, oy))
        pygame.display.flip()

    def _draw_hud(self, surf):
        score_txt = self.font_med.render(f"SCORE  {int(self.score)}", True, TEXT_COLOR)
        surf.blit(score_txt, (16, 12))

        time_txt = self.font_small.render(
            f"TIME  {self.survival_time:5.1f}s", True, DIM_TEXT)
        surf.blit(time_txt, (16, 46))

        hs_txt = self.font_small.render(
            f"BEST  {self.highscore}", True, DIM_TEXT)
        surf.blit(hs_txt, (WIDTH - hs_txt.get_width() - 16, 12))

        diff_txt = self.font_small.render(
            f"WAVE  {self.difficulty_level + 1}", True, DIM_TEXT)
        surf.blit(diff_txt, (WIDTH - diff_txt.get_width() - 16, 34))

        if self.combo_active:
            combo_txt = self.font_med.render(
                f"COMBO x{COMBO_MULTIPLIER}", True, (255, 200, 80))
            surf.blit(combo_txt, (WIDTH // 2 - combo_txt.get_width() // 2, 12))

    def _draw_center_text(self, surf, title, subtitle):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surf.blit(overlay, (0, 0))

        t = self.font_big.render(title, True, TEXT_COLOR)
        surf.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2 - 60))
        s = self.font_small.render(subtitle, True, DIM_TEXT)
        surf.blit(s, (WIDTH // 2 - s.get_width() // 2, HEIGHT // 2 + 10))

    def _draw_game_over(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surf.blit(overlay, (0, 0))

        title = self.font_big.render("GAME OVER", True, (255, 90, 90))
        surf.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 130))

        score_txt = self.font_med.render(
            f"FINAL SCORE  {int(self.score)}", True, TEXT_COLOR)
        surf.blit(score_txt, (WIDTH // 2 - score_txt.get_width() // 2, HEIGHT // 2 - 50))

        time_txt = self.font_med.render(
            f"SURVIVED  {self.survival_time:5.1f}s", True, TEXT_COLOR)
        surf.blit(time_txt, (WIDTH // 2 - time_txt.get_width() // 2, HEIGHT // 2 - 10))

        hs_txt = self.font_med.render(
            f"BEST  {self.highscore}", True, (255, 200, 80))
        surf.blit(hs_txt, (WIDTH // 2 - hs_txt.get_width() // 2, HEIGHT // 2 + 30))

        hint = self.font_small.render(
            "Press R to restart   |   Esc to quit", True, DIM_TEXT)
        surf.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 90))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error:
        pass  # audio optional

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Asteroid Splitter")
    clock = pygame.time.Clock()

    game = Game(screen)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 0.05)  # clamp for stability

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            result = game.handle_event(event)
            if result == "quit":
                running = False
                break

        if not running:
            break

        game.update(dt)
        game.draw()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
