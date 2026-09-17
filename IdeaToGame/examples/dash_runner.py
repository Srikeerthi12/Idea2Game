
"""
Dash Runner — a 2D endless runner built with Pygame.

Controls:
    SPACE / UP    -> Jump (hold for higher jump, release early for a short hop)
    SPACE / ENTER -> Start / Restart
    ESC           -> Quit

Everything is drawn with primitives; no external assets required.
"""

import sys
import math
import random
import pygame

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 800, 400
FPS = 60

GROUND_Y = HEIGHT - 60          # top of the ground strip
GRAVITY = 0.9
JUMP_VELOCITY = -16
BASE_SPEED = 6.0
MAX_SPEED = 16.0
SPEED_INCREMENT = 0.5           # added every SPEED_INTERVAL seconds
SPEED_INTERVAL = 10.0           # seconds between speed bumps

SPAWN_MIN = 0.9                 # seconds
SPAWN_MAX = 1.8                 # seconds

COYOTE_TIME = 0.08              # seconds of grace after leaving ground
JUMP_BUFFER = 0.12              # seconds a jump press is remembered

# Colors
SKY_TOP = (135, 206, 235)
SKY_BOTTOM = (200, 235, 255)
GROUND_COLOR = (222, 184, 135)
GROUND_DARK = (180, 140, 100)
PLAYER_COLOR = (60, 90, 200)
PLAYER_DARK = (40, 60, 150)
OBSTACLE_COLOR = (60, 160, 70)
OBSTACLE_DARK = (35, 110, 45)
TEXT_COLOR = (30, 30, 40)
HILL_COLOR = (170, 200, 170)
CLOUD_COLOR = (255, 255, 255)

# Game states
TITLE, PLAYING, GAME_OVER = 0, 1, 2


# ---------------------------------------------------------------------------
# Helper: simple tone generator for sound effects (no external files)
# ---------------------------------------------------------------------------
def make_tone(frequency, duration_ms, volume=0.3):
    """Generate a simple sine-wave Sound. Returns None if mixer unavailable."""
    try:
        if not pygame.mixer.get_init():
            return None
        sample_rate = pygame.mixer.get_init()[0]
        n_samples = int(sample_rate * duration_ms / 1000.0)
        buf = bytearray()
        for i in range(n_samples):
            # fade out to avoid clicks
            fade = 1.0 - (i / n_samples)
            value = int(127 * volume * fade *
                        math.sin(2 * math.pi * frequency * i / sample_rate))
            buf.append(max(0, min(255, value + 128)))
        return pygame.mixer.Sound(buffer=bytes(buf))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
class Player:
    def __init__(self):
        self.w, self.h = 40, 60
        self.x = WIDTH // 5
        self.y = GROUND_Y - self.h
        self.vy = 0.0
        self.on_ground = True
        self.coyote_timer = 0.0
        self.jump_buffer_timer = 0.0
        self.jump_held = False
        # squash & stretch
        self.scale_x = 1.0
        self.scale_y = 1.0

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def request_jump(self):
        self.jump_buffer_timer = JUMP_BUFFER

    def release_jump(self):
        self.jump_held = False
        # variable jump height: cut upward velocity
        if self.vy < 0:
            self.vy *= 0.5

    def update(self, dt):
        # timers
        if self.coyote_timer > 0:
            self.coyote_timer -= dt
        if self.jump_buffer_timer > 0:
            self.jump_buffer_timer -= dt

        # perform jump if buffered and (grounded or within coyote time)
        if self.jump_buffer_timer > 0 and (self.on_ground or self.coyote_timer > 0):
            self.vy = JUMP_VELOCITY
            self.on_ground = False
            self.coyote_timer = 0.0
            self.jump_buffer_timer = 0.0
            self.jump_held = True
            # stretch on takeoff
            self.scale_x = 0.8
            self.scale_y = 1.2
            return True  # signal that a jump happened

        # gravity
        self.vy += GRAVITY
        self.y += self.vy

        # ground collision
        if self.y + self.h >= GROUND_Y:
            if not self.on_ground:
                # landing squash
                self.scale_x = 1.25
                self.scale_y = 0.75
            self.y = GROUND_Y - self.h
            self.vy = 0.0
            self.on_ground = True
            self.coyote_timer = COYOTE_TIME
        else:
            if self.on_ground:
                self.coyote_timer = COYOTE_TIME
            self.on_ground = False

        # ease scale back to 1
        self.scale_x += (1.0 - self.scale_x) * 0.2
        self.scale_y += (1.0 - self.scale_y) * 0.2
        return False

    def draw(self, surf):
        r = self.rect
        dw = max(1, int(self.w * self.scale_x))
        dh = max(1, int(self.h * self.scale_y))
        dx = r.x + (self.w - dw) // 2
        dy = r.bottom - dh
        body = pygame.Rect(dx, dy, dw, dh)
        pygame.draw.rect(surf, PLAYER_COLOR, body, border_radius=6)
        pygame.draw.rect(surf, PLAYER_DARK, body, width=3, border_radius=6)
        # simple "eye" to give it character
        eye = pygame.Rect(body.x + dw - 14, body.y + 10, 6, 6)
        pygame.draw.rect(surf, (255, 255, 255), eye)


# ---------------------------------------------------------------------------
# Obstacle
# ---------------------------------------------------------------------------
class Obstacle:
    def __init__(self, x, w, h, kind="block"):
        self.x = x
        self.w = w
        self.h = h
        self.kind = kind
        self.passed = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x), GROUND_Y - self.h, self.w, self.h)

    def update(self, speed):
        self.x -= speed

    def draw(self, surf):
        r = self.rect
        pygame.draw.rect(surf, OBSTACLE_COLOR, r, border_radius=4)
        pygame.draw.rect(surf, OBSTACLE_DARK, r, width=3, border_radius=4)
        # little detail lines
        if self.kind == "spike":
            pygame.draw.polygon(surf, OBSTACLE_DARK,
                                [(r.x, r.bottom), (r.centerx, r.y), (r.right, r.bottom)], 3)


# ---------------------------------------------------------------------------
# Particle (dust)
# ---------------------------------------------------------------------------
class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-2.5, -0.5)
        self.vy = random.uniform(-2.5, -0.5)
        self.life = 0.5
        self.max_life = 0.5
        self.radius = random.randint(2, 4)

    def update(self, dt):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.15
        self.life -= dt

    def draw(self, surf):
        if self.life > 0:
            alpha = max(0, min(255, int(255 * (self.life / self.max_life))))
            s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (200, 180, 150, alpha),
                               (self.radius, self.radius), self.radius)
            surf.blit(s, (int(self.x - self.radius), int(self.y - self.radius)))


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            pass

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Dash Runner")
        self.clock = pygame.time.Clock()

        self.font_big = pygame.font.SysFont("consolas", 48, bold=True)
        self.font_med = pygame.font.SysFont("consolas", 28, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 20)

        # sounds
        self.snd_jump = make_tone(660, 90, 0.25)
        self.snd_death = make_tone(140, 300, 0.35)
        self.snd_point = make_tone(880, 60, 0.2)

        self.high_score = 0
        self.state = TITLE

        # parallax background offsets
        self.bg_offset = 0.0
        self.hill_offset = 0.0
        self.clouds = [{"x": random.randint(0, WIDTH), "y": random.randint(30, 140),
                        "s": random.uniform(0.6, 1.4)} for _ in range(5)]

        # screen shake
        self.shake_timer = 0.0
        self.shake_mag = 0.0

        self.reset()

    # ------------------------------------------------------------------
    def reset(self):
        self.player = Player()
        self.obstacles = []
        self.particles = []
        self.score = 0
        self.speed = BASE_SPEED
        self.elapsed = 0.0
        self.spawn_timer = random.uniform(SPAWN_MIN, SPAWN_MAX)
        self.speed_timer = 0.0
        self.bg_offset = 0.0
        self.hill_offset = 0.0
        self.shake_timer = 0.0
        self.shake_mag = 0.0

    # ------------------------------------------------------------------
    def spawn_obstacle(self):
        # difficulty scaling based on speed
        difficulty = (self.speed - BASE_SPEED) / (MAX_SPEED - BASE_SPEED + 0.001)
        difficulty = max(0.0, min(1.0, difficulty))

        roll = random.random()
        if roll < 0.45:
            # low obstacle
            w, h, kind = random.randint(24, 34), random.randint(30, 45), "block"
        elif roll < 0.75:
            # tall obstacle
            w, h, kind = random.randint(24, 34), random.randint(55, 75), "block"
        elif roll < 0.9:
            # wide obstacle
            w, h, kind = random.randint(55, 80), random.randint(30, 45), "block"
        else:
            # spike
            w, h, kind = random.randint(28, 40), random.randint(40, 60), "spike"

        self.obstacles.append(Obstacle(WIDTH + 20, w, h, kind))

        # double obstacle appears later in the run
        if difficulty > 0.35 and random.random() < 0.25 * difficulty:
            gap = random.randint(30, 55)
            w2 = random.randint(24, 34)
            h2 = random.randint(30, 55)
            self.obstacles.append(Obstacle(WIDTH + 20 + w + gap, w2, h2, "block"))

    # ------------------------------------------------------------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.quit()
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if self.state == TITLE:
                        self.reset()
                        self.state = PLAYING
                    elif self.state == GAME_OVER:
                        self.reset()
                        self.state = PLAYING
                    elif self.state == PLAYING:
                        self.player.request_jump()
                elif event.key == pygame.K_UP and self.state == PLAYING:
                    self.player.request_jump()
            elif event.type == pygame.KEYUP:
                if event.key in (pygame.K_SPACE, pygame.K_UP):
                    if self.state == PLAYING:
                        self.player.release_jump()

    # ------------------------------------------------------------------
    def update(self, dt):
        # background always scrolls a little for life
        self.bg_offset += (self.speed * 0.15) if self.state == PLAYING else 0.5
        self.hill_offset += (self.speed * 0.35) if self.state == PLAYING else 1.0

        for c in self.clouds:
            c["x"] -= 0.3 * c["s"] * (self.speed / BASE_SPEED if self.state == PLAYING else 1)
            if c["x"] < -80:
                c["x"] = WIDTH + random.randint(20, 120)
                c["y"] = random.randint(30, 140)

        if self.shake_timer > 0:
            self.shake_timer -= dt

        if self.state != PLAYING:
            # still update particles for polish
            for p in self.particles:
                p.update(dt)
            self.particles = [p for p in self.particles if p.life > 0]
            return

        # --- difficulty ramp ---
        self.elapsed += dt
        self.speed_timer += dt
        if self.speed_timer >= SPEED_INTERVAL:
            self.speed_timer -= SPEED_INTERVAL
            self.speed = min(MAX_SPEED, self.speed + SPEED_INCREMENT)

        # --- player ---
        jumped = self.player.update(dt)
        if jumped and self.snd_jump:
            self.snd_jump.play()

        # --- spawn ---
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_obstacle()
            # gap scales with speed so it stays fair
            speed_factor = BASE_SPEED / self.speed
            self.spawn_timer = random.uniform(SPAWN_MIN, SPAWN_MAX) * speed_factor

        # --- obstacles ---
        for ob in self.obstacles:
            ob.update(self.speed)

        # scoring: +5 per obstacle cleared
        for ob in self.obstacles:
            if not ob.passed and ob.x + ob.w < self.player.x:
                ob.passed = True
                self.score += 5
                if self.snd_point:
                    self.snd_point.play()

        # remove off-screen obstacles
        self.obstacles = [ob for ob in self.obstacles if ob.x + ob.w > -20]

        # --- collision ---
        pr = self.player.rect
        for ob in self.obstacles:
            if pr.colliderect(ob.rect):
                self.game_over()
                return

        # --- distance score ---
        self.score += 1

        # --- particles ---
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]

        # dust when running on ground
        if self.player.on_ground and random.random() < 0.3:
            self.particles.append(Particle(self.player.x, GROUND_Y - 2))

    # ------------------------------------------------------------------
    def game_over(self):
        self.state = GAME_OVER
        self.shake_timer = 0.25
        self.shake_mag = 8.0
        if self.snd_death:
            self.snd_death.play()
        if self.score > self.high_score:
            self.high_score = self.score
        # burst of particles
        for _ in range(20):
            self.particles.append(Particle(self.player.x + self.player.w // 2,
                                           self.player.y + self.player.h // 2))

    # ------------------------------------------------------------------
    def draw_background(self):
        # sky gradient
        for i in range(HEIGHT):
            t = i / HEIGHT
            r = int(SKY_TOP[0] + (SKY_BOTTOM[0] - SKY_TOP[0]) * t)
            g = int(SKY_TOP[1] + (SKY_BOTTOM[1] - SKY_TOP[1]) * t)
            b = int(SKY_TOP[2] + (SKY_BOTTOM[2] - SKY_TOP[2]) * t)
            pygame.draw.line(self.screen, (r, g, b), (0, i), (WIDTH, i))

        # clouds
        for c in self.clouds:
            x, y, s = int(c["x"]), int(c["y"]), c["s"]
            w = int(60 * s)
            h = int(24 * s)
            pygame.draw.ellipse(self.screen, CLOUD_COLOR, (x, y, w, h))
            pygame.draw.ellipse(self.screen, CLOUD_COLOR, (x + w // 3, y - h // 2, w, h))
            pygame.draw.ellipse(self.screen, CLOUD_COLOR, (x + w // 2, y, w, h))

        # parallax hills
        hill_y = GROUND_Y - 40
        offset = int(self.hill_offset) % 200
        for i in range(-1, WIDTH // 200 + 2):
            hx = i * 200 - offset
            pygame.draw.polygon(self.screen, HILL_COLOR,
                                [(hx, GROUND_Y), (hx + 100, hill_y), (hx + 200, GROUND_Y)])

    def draw_ground(self):
        pygame.draw.rect(self.screen, GROUND_COLOR, (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
        pygame.draw.line(self.screen, GROUND_DARK, (0, GROUND_Y), (WIDTH, GROUND_Y), 3)
        # scrolling dashes
        offset = int(self.bg_offset) % 40
        for x in range(-40, WIDTH + 40, 40):
            pygame.draw.line(self.screen, GROUND_DARK,
                             (x - offset, GROUND_Y + 20),
                             (x - offset + 20, GROUND_Y + 20), 3)

    def draw_hud(self):
        score_surf = self.font_med.render(f"Score: {self.score}", True, TEXT_COLOR)
        self.screen.blit(score_surf, (WIDTH - score_surf.get_width() - 20, 15))
        hs_surf = self.font_small.render(f"Best: {self.high_score}", True, TEXT_COLOR)
        self.screen.blit(hs_surf, (WIDTH - hs_surf.get_width() - 20, 50))

    def draw_title(self):
        title = self.font_big.render("DASH RUNNER", True, TEXT_COLOR)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 90))
        sub = self.font_med.render("Press SPACE to start", True, TEXT_COLOR)
        self.screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 170))
        ctrl = self.font_small.render("SPACE / UP = Jump    ESC = Quit", True, TEXT_COLOR)
        self.screen.blit(ctrl, (WIDTH // 2 - ctrl.get_width() // 2, 220))
        if self.high_score > 0:
            hs = self.font_small.render(f"Best: {self.high_score}", True, TEXT_COLOR)
            self.screen.blit(hs, (WIDTH // 2 - hs.get_width() // 2, 260))

    def draw_game_over(self):
        over = self.font_big.render("GAME OVER", True, (180, 40, 40))
        self.screen.blit(over, (WIDTH // 2 - over.get_width() // 2, 90))
        sc = self.font_med.render(f"Score: {self.score}", True, TEXT_COLOR)
        self.screen.blit(sc, (WIDTH // 2 - sc.get_width() // 2, 160))
        hs = self.font_med.render(f"Best: {self.high_score}", True, TEXT_COLOR)
        self.screen.blit(hs, (WIDTH // 2 - hs.get_width() // 2, 200))
        sub = self.font_small.render("Press SPACE to restart", True, TEXT_COLOR)
        self.screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 250))

    # ------------------------------------------------------------------
    def draw(self):
        # screen shake offset
        shake_x = shake_y = 0
        if self.shake_timer > 0:
            shake_x = random.randint(-int(self.shake_mag), int(self.shake_mag))
            shake_y = random.randint(-int(self.shake_mag), int(self.shake_mag))

        # draw everything onto the screen
        self.draw_background()
        self.draw_ground()

        for ob in self.obstacles:
            ob.draw(self.screen)

        for p in self.particles:
            p.draw(self.screen)

        if self.state != TITLE:
            self.player.draw(self.screen)

        if self.state == PLAYING:
            self.draw_hud()
        elif self.state == TITLE:
            self.draw_title()
        elif self.state == GAME_OVER:
            self.draw_game_over()

        # apply shake by blitting a shifted copy
        if shake_x or shake_y:
            snapshot = self.screen.copy()
            self.screen.fill((0, 0, 0))
            self.screen.blit(snapshot, (shake_x, shake_y))

        pygame.display.flip()

    # ------------------------------------------------------------------
    def quit(self):
        pygame.quit()
        sys.exit()

    # ------------------------------------------------------------------
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)  # clamp to avoid huge steps
            self.handle_events()
            self.update(dt)
            self.draw()


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    Game().run()