"""
TSUNAMI DEFENSE - Defend the city against ever-bigger waves!
=============================================================
How to play:
  * Waves come from the ocean (left) and move toward the city (right).
  * Between waves is BUILD phase. Click a glowing ground slot to select it,
    then build a defense (buttons at the bottom, or keys 1 / 2 / 3):
        1 = Wall        $50   - blocks the wave, soaks up damage
        2 = Cannon      $100  - shoots the wave, reduces its power
        3 = Frost Tower $120  - shoots the wave AND slows it down
  * Click a built defense to select it, then:
        U = Upgrade ($75, +damage/HP)    X = Sell (70% refund)
  * SPACE = start the next wave     P = pause     R = repair city ($75, +20 HP)
  * If a wave reaches the city, the city loses HP. City HP = 0 -> game over.
  * Destroy a wave before it reaches the city to earn money.
  * Every wave is taller, tougher and a bit faster than the last.
    Later rounds send several waves in a row. Good luck!

Run:  python tsunami_defense.py
Test: set TSUNAMI_TEST=1 to run a 300-frame headless smoke test.
"""
import os
import sys
import math
import random
import array
import json
import threading
import time
import urllib.request
import urllib.error

import pygame

# ---------------------------------------------------------------- constants
WIDTH, HEIGHT = 1280, 720
GROUND_Y = 620
CITY_X = 990
OCEAN_W = 470
FPS = 60

SLOT_XS = [545, 630, 715, 800, 885]

COSTS = {"wall": 50, "cannon": 100, "frost": 120}
UPGRADE_COST = 75
REPAIR_COST = 75
REPAIR_AMOUNT = 20
SELL_REFUND = 0.7

VERSION = "1.0.0"
UPDATE_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "update_config.json")

# colours
SKY_TOP = (70, 150, 210)
SKY_BOT = (170, 215, 240)
SAND = (232, 205, 145)
OCEAN = (25, 105, 175)
OCEAN_DEEP = (15, 75, 140)
WHITE = (255, 255, 255)
BLACK = (20, 20, 25)
GREY = (90, 95, 105)
GOLD = (255, 200, 40)
RED = (225, 60, 55)
GREEN = (60, 190, 90)
ICE = (140, 225, 255)


# ---------------------------------------------------------------- sounds
# All sound effects are synthesized in code (sine sweeps / noise bursts),
# so the game needs no audio files. Press M in-game to mute / unmute.
def _tone(freq_a, freq_b, duration, volume=0.3, noise=False):
    rate = 22050
    n = max(1, int(rate * duration))
    samples = array.array("h")
    for i in range(n):
        t = i / rate
        frac = i / n
        env = (1.0 - frac) ** 1.6 * min(1.0, frac * 30 + 0.15)
        if noise:
            value = (random.random() * 2 - 1) * env
        else:
            freq = freq_a + (freq_b - freq_a) * frac
            value = math.sin(math.tau * freq * t) * env
        samples.append(int(max(-1.0, min(1.0, value)) * volume * 32767))
    return pygame.mixer.Sound(buffer=samples.tobytes())


def _melody(notes, volume=0.3):
    rate = 22050
    samples = array.array("h")
    for freq, duration in notes:
        n = max(1, int(rate * duration))
        for i in range(n):
            t = i / rate
            frac = i / n
            env = (1.0 - frac) * min(1.0, frac * 25 + 0.2)
            value = math.sin(math.tau * freq * t) * env
            samples.append(int(value * volume * 32767))
    return pygame.mixer.Sound(buffer=samples.tobytes())


class SoundFX:
    def __init__(self):
        self.enabled = False
        self.muted = False
        self.sounds = {}
        self._last_played = {}

    def init(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(8)
            pygame.mixer.set_reserved(1)  # channel 0 is reserved for music
            self.sounds = {
                "click": _tone(700, 700, 0.05, 0.18),
                "build": _melody([(392, 0.07), (523, 0.07), (659, 0.11)], 0.32),
                "error": _tone(170, 105, 0.18, 0.3),
                "coin": _melody([(988, 0.06), (1319, 0.15)], 0.3),
                "upgrade": _melody([(523, 0.07), (659, 0.07), (784, 0.07), (1047, 0.13)], 0.32),
                "repair": _melody([(660, 0.08), (880, 0.13)], 0.3),
                "shoot": _tone(880, 220, 0.09, 0.22),
                "frost": _tone(1250, 1750, 0.13, 0.2),
                "hit": _tone(300, 140, 0.07, 0.2, noise=True),
                "splash": _tone(0, 0, 0.45, 0.38, noise=True),
                "thud": _tone(95, 52, 0.15, 0.5),
                "boom": _tone(0, 0, 0.7, 0.55, noise=True),
                "alarm": _melody([(440, 0.14), (440, 0.14), (587, 0.22)], 0.32),
                "clear": _melody([(523, 0.09), (659, 0.09), (784, 0.09), (1047, 0.16)], 0.32),
                "gameover": _melody([(392, 0.22), (330, 0.22), (262, 0.22), (196, 0.4)], 0.34),
            }
            self.enabled = True
        except Exception as exc:  # audio is optional - game runs silently without it
            print(f"Sound disabled ({exc})")
            self.enabled = False

    def play(self, name, min_gap_ms=60):
        if not self.enabled or self.muted:
            return
        sound = self.sounds.get(name)
        if sound is None:
            return
        now = pygame.time.get_ticks()
        if now - self._last_played.get(name, -10 ** 9) < min_gap_ms:
            return
        self._last_played[name] = now
        try:
            sound.play()
        except Exception:
            pass

    def toggle_mute(self):
        self.muted = not self.muted
        return self.muted


SFX = SoundFX()


# ---------------------------------------------------------------- music
# Two synthesized loops (no audio files): a calm "build" loop and a
# faster "battle" loop over the same Am - F - C - G progression, so
# switching tracks at wave start / clear feels seamless.
# N toggles music on/off, M mutes music + sound effects together.
def _midi_freq(midi):
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def _render_music_loop(kind):
    rate = 22050
    bpm = 138 if kind == "battle" else 92
    spb = 60.0 / bpm
    bars = 4
    total = int(rate * spb * 4 * bars)
    mix = array.array("f", [0.0] * total)
    chords = [[57, 60, 64], [53, 57, 60], [55, 60, 64], [55, 59, 62]]
    roots = [45, 41, 48, 43]
    melody = [[69, 72, 76, 72, 74, 72, 69, 0], [65, 69, 72, 69, 72, 69, 65, 0], [67, 72, 76, 72, 76, 79, 76, 0], [67, 71, 74, 71, 74, 79, 74, 0]]

    def add_tone(midi, start_beat, dur_beats, volume, harmonics=((1, 1.0),)):
        if not midi:
            return
        freq = _midi_freq(midi)
        start = int(start_beat * spb * rate)
        n = int(dur_beats * spb * rate)
        for i in range(n):
            idx = start + i
            if idx >= total:
                break
            t = i / rate
            attack = min(1.0, i / (rate * 0.03 + 1))
            release = min(1.0, (n - i) / (rate * 0.05 + 1))
            env = attack * release
            value = 0.0
            for mult, amp in harmonics:
                value += amp * math.sin(math.tau * freq * mult * t)
            mix[idx] += value * env * volume

    def add_noise(start_beat, dur_beats, volume):
        start = int(start_beat * spb * rate)
        n = int(dur_beats * spb * rate)
        for i in range(n):
            idx = start + i
            if idx >= total:
                break
            frac = i / n
            mix[idx] += (random.random() * 2 - 1) * (1.0 - frac) ** 1.5 * volume

    def add_kick(start_beat):
        start = int(start_beat * spb * rate)
        n = int(rate * 0.22)
        for i in range(n):
            idx = start + i
            if idx >= total:
                break
            t = i / rate
            frac = i / n
            freq = 130 + (48 - 130) * frac
            mix[idx] += math.sin(math.tau * freq * t) * (1.0 - frac) ** 1.4 * 0.5

    for bar in range(bars):
        base = bar * 4.0
        chord = chords[bar]
        root = roots[bar]
        if kind == "build":
            for note in chord:
                add_tone(note, base, 4.0, 0.055)
            add_tone(root, base, 2.0, 0.16, ((1, 1.0), (2, 0.35)))
            add_tone(root, base + 2.0, 2.0, 0.16, ((1, 1.0), (2, 0.35)))
            for step in range(8):
                note = chord[step % 3] + (12 if step % 4 >= 2 else 0)
                add_tone(note, base + step * 0.5, 0.45, 0.07, ((1, 1.0), (2, 0.25)))
            add_noise(base + 1.0, 0.08, 0.018)
            add_noise(base + 3.0, 0.08, 0.018)
        else:
            for step in range(8):
                note = root + (12 if step in (2, 6) else 0)
                add_tone(note, base + step * 0.5, 0.42, 0.19, ((1, 1.0), (2, 0.3)))
            for beat in range(4):
                add_kick(base + beat)
                add_noise(base + beat + 0.5, 0.07, 0.045)
            add_noise(base + 1.0, 0.18, 0.10)
            add_noise(base + 3.0, 0.18, 0.10)
            for note in chord:
                add_tone(note, base, 0.3, 0.05, ((1, 1.0), (3, 0.2)))
                add_tone(note, base + 2.5, 0.3, 0.05, ((1, 1.0), (3, 0.2)))
            for step, note in enumerate(melody[bar]):
                add_tone(note, base + step * 0.5, 0.46, 0.075, ((1, 1.0), (2, 0.3)))
    samples = array.array("h")
    for value in mix:
        samples.append(int(max(-1.0, min(1.0, value)) * 0.9 * 32767))
    return pygame.mixer.Sound(buffer=samples.tobytes())


class MusicPlayer:
    def __init__(self):
        self.enabled = False
        self.muted = False
        self.music_on = True
        self.tracks = {}
        self.channel = None
        self.current = None

    def init(self):
        try:
            if not pygame.mixer.get_init():
                return
            self.tracks = {"build": _render_music_loop("build"), "battle": _render_music_loop("battle")}
            self.channel = pygame.mixer.Channel(0)
            self.channel.set_volume(0.45)
            self.enabled = True
            self.play("build")
        except Exception as exc:  # music is optional - game runs without it
            print(f"Music disabled ({exc})")
            self.enabled = False

    def play(self, name):
        sound = self.tracks.get(name)
        if not self.enabled or sound is None:
            return
        self.current = name
        self.channel.play(sound, loops=-1, fade_ms=450)

    def toggle_music(self):
        self.music_on = not self.music_on
        if self.enabled and not self.music_on:
            self.channel.stop()
            self.current = None
        return self.music_on

    def refresh(self, phase, paused):
        if not self.enabled or not self.music_on:
            return
        desired = "battle" if phase == "wave" else "build" if phase == "build" else None
        if desired is None:  # game over - fade the music out
            if self.current is not None:
                self.channel.fadeout(350)
                self.current = None
            return
        if paused or self.muted:
            self.channel.pause()
            return
        self.channel.unpause()
        if self.current != desired:
            self.play(desired)


MUSIC = MusicPlayer()


# ---------------------------------------------------------------- entities
class Wave:
    """One tsunami. Bigger (taller / tougher / faster) every round."""

    def __init__(self, number, scale=1.0):
        self.number = number
        self.height = min(480, (120 + number * 34) * scale)
        self.width = 150 + number * 6
        self.max_hp = (110 * (1.55 ** (number - 1))) * scale
        self.hp = self.max_hp
        self.speed = min(135, (52 + number * 6) * (0.95 + 0.05 * scale))
        self.x = -self.width - 30
        self.slow_until = 0
        self.bob_phase = random.uniform(0, math.tau)
        self.dead = False
        self.hit_city = False

    @property
    def front(self):
        return self.x + self.width

    def is_slowed(self, now):
        return now < self.slow_until

    def update(self, dt, now, blockers):
        """Move right unless a wall is in the way. Returns wall being hit."""
        speed = self.speed * (0.55 if self.is_slowed(now) else 1.0)
        hitting = None
        for b in blockers:
            if b.kind == "wall" and b.hp > 0:
                if self.front >= b.x - 4 and self.x < b.x:
                    hitting = b
                    break
        if hitting is None:
            self.x += speed * dt
        return hitting

    def draw(self, surf, now):
        h = self.height * max(0.12, self.hp / self.max_hp) if self.max_hp else self.height
        top = GROUND_Y - h
        bob = math.sin(now * 2.2 + self.bob_phase) * 5
        top += bob
        # body - a big curling wave shape
        pts = []
        steps = 18
        for i in range(steps + 1):
            t = i / steps
            px = self.x + t * self.width
            # crest curls forward at the top
            py = top + (t ** 2.2) * (GROUND_Y - top) * 0.92
            pts.append((px, py))
        body = pts + [(self.front, GROUND_Y), (self.x, GROUND_Y)]
        colour = (35, 130, 205) if not self.is_slowed(now) else (70, 165, 220)
        pygame.draw.polygon(surf, colour, body)
        pygame.draw.polygon(surf, (90, 190, 240), pts, 0) if False else None
        # foam crest
        for (px, py) in pts[::3]:
            pygame.draw.circle(surf, WHITE, (int(px), int(py)), random.randint(4, 9))
        pygame.draw.circle(surf, WHITE, (int(self.front - 8), int(top + 14)), 16)
        pygame.draw.circle(surf, WHITE, (int(self.front - 30), int(top + 8)), 11)
        # HP bar
        if self.hp < self.max_hp:
            w = 110
            bx, by = self.x + self.width / 2 - w / 2, max(8, top - 26)
            pygame.draw.rect(surf, BLACK, (bx - 1, by - 1, w + 2, 10))
            pygame.draw.rect(surf, RED, (bx, by, w, 8))
            pygame.draw.rect(surf, GREEN, (bx, by, w * max(0, self.hp / self.max_hp), 8))


class Structure:
    def __init__(self, kind, slot):
        self.kind = kind
        self.slot = slot
        self.x = SLOT_XS[slot]
        self.level = 1
        self.cooldown = 0.0
        if kind == "wall":
            self.max_hp = 220
        elif kind == "cannon":
            self.max_hp = 90
        else:  # frost
            self.max_hp = 80
        self.hp = self.max_hp

    @property
    def damage(self):
        base = {"cannon": 26, "frost": 13}.get(self.kind, 0)
        return base * (1 + 0.6 * (self.level - 1))

    @property
    def range(self):
        return 520 if self.kind in ("cannon", "frost") else 0

    @property
    def fire_rate(self):
        return 0.55 if self.kind == "cannon" else 0.85

    def upgrade(self):
        self.level += 1
        if self.kind == "wall":
            self.max_hp += 130
            self.hp += 130
        else:
            self.max_hp += 35
            self.hp += 35

    def rect(self):
        if self.kind == "wall":
            return pygame.Rect(self.x - 26, GROUND_Y - 150, 52, 150)
        return pygame.Rect(self.x - 26, GROUND_Y - 78, 52, 78)

    def draw(self, surf, selected, font):
        r = self.rect()
        if selected:
            pygame.draw.rect(surf, GOLD, r.inflate(8, 8), 3, border_radius=6)
            if self.range:
                pygame.draw.circle(surf, (255, 255, 255), (self.x, GROUND_Y - 40), self.range, 1)
        if self.kind == "wall":
            pygame.draw.rect(surf, (130, 130, 140), r, border_radius=4)
            pygame.draw.rect(surf, (165, 165, 175), r, 3, border_radius=4)
            for yy in range(r.top + 18, r.bottom - 6, 26):
                pygame.draw.line(surf, (100, 100, 110), (r.left + 4, yy), (r.right - 4, yy), 2)
        elif self.kind == "cannon":
            pygame.draw.rect(surf, (70, 80, 95), (self.x - 24, GROUND_Y - 26, 48, 26), border_radius=4)
            pygame.draw.circle(surf, (45, 55, 70), (self.x, GROUND_Y - 30), 20)
            pygame.draw.rect(surf, BLACK, (self.x - 34, GROUND_Y - 38, 30, 9), border_radius=4)
            pygame.draw.circle(surf, GOLD, (self.x, GROUND_Y - 30), 6)
        else:  # frost
            pygame.draw.rect(surf, (90, 160, 200), (self.x - 24, GROUND_Y - 26, 48, 26), border_radius=4)
            pygame.draw.circle(surf, ICE, (self.x, GROUND_Y - 42), 19)
            pygame.draw.circle(surf, WHITE, (self.x, GROUND_Y - 42), 9)
        # level pips + hp bar (damaged only)
        for i in range(self.level):
            pygame.draw.circle(surf, GOLD, (self.x - 14 + i * 14, GROUND_Y + 16), 4)
        if self.hp < self.max_hp:
            w = 52
            pygame.draw.rect(surf, BLACK, (self.x - w / 2 - 1, r.top - 13, w + 2, 8))
            pygame.draw.rect(surf, GREEN, (self.x - w / 2, r.top - 12, w * max(0, self.hp / self.max_hp), 6))


class Projectile:
    def __init__(self, x, y, target, damage, kind):
        self.x, self.y = x, y
        self.target = target
        self.damage = damage
        self.kind = kind
        self.speed = 620
        self.dead = False

    def update(self, dt, now, particles):
        if self.target.dead:
            self.dead = True
            return
        tx = self.target.x + self.target.width * 0.7
        ty = GROUND_Y - self.target.height * 0.55
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy) or 1
        if dist < 22:
            self.target.hp -= self.damage
            SFX.play("hit", 80)
            if self.kind == "frost":
                self.target.slow_until = now + 1.6
            for _ in range(7):
                particles.append(Particle(tx, ty, ICE if self.kind == "frost" else GOLD))
            self.dead = True
            return
        self.x += dx / dist * self.speed * dt
        self.y += dy / dist * self.speed * dt

    def draw(self, surf):
        colour = ICE if self.kind == "frost" else (255, 170, 50)
        pygame.draw.circle(surf, colour, (int(self.x), int(self.y)), 6)
        pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), 2)


class Particle:
    def __init__(self, x, y, colour):
        self.x, self.y = x, y
        self.vx = random.uniform(-170, 170)
        self.vy = random.uniform(-260, -30)
        self.life = random.uniform(0.35, 0.8)
        self.colour = colour
        self.size = random.randint(2, 6)

    def update(self, dt):
        self.life -= dt
        self.vy += 520 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    def draw(self, surf):
        if self.life > 0:
            pygame.draw.circle(surf, self.colour, (int(self.x), int(self.y)), self.size)


# ---------------------------------------------------------------- drawing helpers
def draw_background(surf, now):
    for y in range(0, GROUND_Y, 4):
        t = y / GROUND_Y
        c = tuple(int(SKY_TOP[i] + (SKY_BOT[i] - SKY_TOP[i]) * t) for i in range(3))
        pygame.draw.line(surf, c, (0, y), (WIDTH, y), 4)
    # sun + clouds
    pygame.draw.circle(surf, (255, 225, 90), (1130, 82), 34)
    for cx, cy, s in [(180, 80, 1.0), (520, 55, 0.7), (820, 105, 0.85)]:
        ox = (now * 6 * s) % (WIDTH + 220) - 110
        for dx, dy, r in [(0, 0, 26), (24, 4, 20), (-24, 5, 19)]:
            pygame.draw.circle(surf, WHITE, (int(cx + ox * 0.1 + dx * s), int(cy + dy)), int(r * s))
    # ocean
    pygame.draw.rect(surf, OCEAN, (0, GROUND_Y - 46, OCEAN_W + 60, HEIGHT - GROUND_Y + 46))
    pygame.draw.rect(surf, OCEAN_DEEP, (0, GROUND_Y + 22, OCEAN_W + 60, HEIGHT - GROUND_Y))
    for i in range(9):
        wx = (i * 67 + now * 40) % (OCEAN_W + 40)
        wy = GROUND_Y - 28 + math.sin(now * 2 + i) * 5
        pygame.draw.arc(surf, WHITE, (wx, wy, 34, 14), 0.2, 2.6, 2)
    # sand / ground
    pygame.draw.rect(surf, SAND, (OCEAN_W - 40, GROUND_Y, WIDTH - OCEAN_W + 40, HEIGHT - GROUND_Y))
    pygame.draw.rect(surf, (198, 168, 110), (0, GROUND_Y, WIDTH, 5))


def draw_city(surf, font, city_hp):
    buildings = [(1005, 300, 62, 320), (1075, 360, 54, 260), (1137, 275, 70, 345), (1215, 335, 56, 285)]
    flash = city_hp <= 30 and (pygame.time.get_ticks() // 400) % 2 == 0
    for (x, top, w, h) in buildings:
        pygame.draw.rect(surf, (105, 115, 135) if not flash else (160, 90, 90), (x, top, w, h))
        pygame.draw.rect(surf, (70, 80, 100), (x, top, w, h), 2)
        for wy in range(top + 16, GROUND_Y - 18, 30):
            for wx in range(x + 9, x + w - 12, 20):
                lit = ((wx * 7 + wy * 13) % 5) != 0
                pygame.draw.rect(surf, (255, 230, 130) if lit else (60, 70, 90), (wx, wy, 11, 14))
    label = font.render("CITY", True, WHITE)
    surf.blit(label, (CITY_X + 105 - label.get_width() // 2, 238))


# ---------------------------------------------------------------- updates
# Shared state written by the background checker thread, read by draw_hud.
UPDATE_STATE = {"latest": None}


def _parse_version(text):
    try:
        return tuple(int(p) for p in str(text).strip().lstrip("v").split("."))
    except Exception:
        return (0,)


def _load_update_config():
    try:
        with open(UPDATE_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        url = str(cfg.get("version_url", "")).strip()
        if not url or "YOUR_USERNAME" in url or "YOUR_REPO" in url:
            return None
        return cfg
    except Exception:
        return None


def _update_checker_loop():
    # First check shortly after launch, then every 60 seconds. Never raises:
    # offline / unconfigured just means no banner is shown.
    time.sleep(5)
    while True:
        try:
            cfg = _load_update_config()
            if cfg:
                req = urllib.request.Request(cfg["version_url"], headers={"User-Agent": "TsunamiDefense"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    latest = resp.read().decode("utf-8", "ignore").strip()
                if latest and _parse_version(latest) > _parse_version(VERSION):
                    UPDATE_STATE["latest"] = latest.lstrip("v")
        except Exception:
            pass
        time.sleep(60)


# ---------------------------------------------------------------- game
class Game:
    def __init__(self):
        self.money = 170
        self.city_hp = 100
        self.city_max = 100
        self.wave_no = 0
        self.phase = "build"  # build | wave | over | win
        self.structures = {}  # slot -> Structure
        self.selected = None  # slot index or None
        self.waves = []
        self.projectiles = []
        self.particles = []
        self.to_spawn = 0
        self.spawn_timer = 0.0
        self.spawn_scale = 1.0
        self.message = "Build defenses, then press SPACE to start Wave 1!"
        self.msg_timer = 6.0
        self.shake = 0.0
        self.paused = False
        self.kills = 0
        self.update_available = None  # synced from UPDATE_STATE in draw_hud

    # ----- economy / actions
    def say(self, text, secs=3.0):
        self.message, self.msg_timer = text, secs

    def build(self, kind):
        if self.selected is None:
            self.say("Click a ground slot first!")
            return
        if self.selected in self.structures:
            self.say("That slot is occupied - select it and press X to sell first.")
            return
        cost = COSTS[kind]
        if self.money < cost:
            self.say(f"Not enough money for a {kind} (${cost}).")
            SFX.play("error", 150)
            return
        self.money -= cost
        self.structures[self.selected] = Structure(kind, self.selected)
        self.say(f"Built a {kind}! (${cost})")
        SFX.play("build")

    def sell_selected(self):
        s = self.structures.pop(self.selected, None) if self.selected is not None else None
        if s:
            refund = int(COSTS[s.kind] * SELL_REFUND + (s.level - 1) * 30)
            self.money += refund
            self.say(f"Sold {s.kind} for ${refund}.")
            SFX.play("coin")

    def upgrade_selected(self):
        s = self.structures.get(self.selected) if self.selected is not None else None
        if not s:
            self.say("Select a built defense to upgrade.")
            return
        if self.money < UPGRADE_COST:
            self.say(f"Upgrade costs ${UPGRADE_COST}.")
            return
        self.money -= UPGRADE_COST
        s.upgrade()
        self.say(f"Upgraded {s.kind} to level {s.level}!")
        SFX.play("upgrade")

    def repair(self):
        if self.city_hp >= self.city_max:
            self.say("City is already at full health.")
        elif self.money < REPAIR_COST:
            self.say(f"Repair costs ${REPAIR_COST}.")
        else:
            self.money -= REPAIR_COST
            self.city_hp = min(self.city_max, self.city_hp + REPAIR_AMOUNT)
            self.say(f"City repaired +{REPAIR_AMOUNT} HP.")
            SFX.play("repair")

    def start_wave(self):
        if self.phase != "build":
            return
        self.wave_no += 1
        self.phase = "wave"
        # round composition: 1 big wave, plus extra waves every other round
        self.to_spawn = 1 + (self.wave_no - 1) // 2
        self.spawn_timer = 0.0
        self.spawn_scale = 1.0
        self.say(f"Wave {self.wave_no} incoming! {self.to_spawn} tsunami(s)!", 3.5)
        SFX.play("alarm")

    # ----- update
    def update(self, dt, now):
        if self.paused or self.phase == "over":
            return
        self.msg_timer = max(0, self.msg_timer - dt)
        self.shake = max(0, self.shake - dt * 22)
        # spawning
        if self.phase == "wave" and self.to_spawn > 0:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                scale = self.spawn_scale
                self.waves.append(Wave(self.wave_no, scale))
                self.spawn_scale *= 0.82  # followers in same round are a bit smaller
                self.to_spawn -= 1
                self.spawn_timer = 3.2
        # waves
        walls = [s for s in self.structures.values() if s.kind == "wall"]
        for w in list(self.waves):
            hitting = w.update(dt, now, walls)
            if hitting is not None:
                # wall and wave grind each other down
                dmg = 85 * dt
                SFX.play("thud", 380)
                hitting.hp -= dmg
                w.hp -= dmg * 1.35
                self.shake = min(7, self.shake + dt * 14)
                if random.random() < 0.35:
                    self.particles.append(Particle(w.front, GROUND_Y - random.uniform(20, 130), WHITE))
                if hitting.hp <= 0:
                    del self.structures[hitting.slot]
                    self.say("A wall was destroyed!")
                    SFX.play("boom")
                    for _ in range(16):
                        self.particles.append(Particle(hitting.x, GROUND_Y - 70, GREY))
            if w.hp <= 0 and not w.dead:
                w.dead = True
                bounty = int(55 + self.wave_no * 16)
                self.money += bounty
                self.kills += 1
                self.say(f"Wave destroyed! +${bounty}", 2.2)
                SFX.play("splash")
                for _ in range(30):
                    self.particles.append(Particle(w.x + w.width / 2, GROUND_Y - w.height / 2, (90, 180, 240)))
            elif w.front >= CITY_X and not w.hit_city:
                w.hit_city = True
                w.dead = True
                dmg_city = int(min(38, 9 + self.wave_no * 3 + 18 * max(0, w.hp / w.max_hp)))
                self.city_hp -= dmg_city
                self.shake = 13
                self.say(f"The tsunami hit the city! -{dmg_city} HP", 3.5)
                SFX.play("boom")
                for _ in range(36):
                    self.particles.append(Particle(CITY_X + 20, GROUND_Y - random.uniform(0, 200), (90, 180, 240)))
                if self.city_hp <= 0:
                    self.city_hp = 0
                    self.phase = "over"
                    SFX.play("gameover")
        self.waves = [w for w in self.waves if not w.dead]
        # towers fire
        for s in self.structures.values():
            s.cooldown -= dt
            if s.kind == "wall" or not self.waves:
                continue
            target = min(self.waves, key=lambda w: abs(w.front - s.x))
            if abs(target.front - s.x) <= s.range and target.x + target.width > 0 and s.cooldown <= 0:
                s.cooldown = s.fire_rate
                self.projectiles.append(Projectile(s.x, GROUND_Y - 46, target, s.damage, s.kind))
                SFX.play("frost" if s.kind == "frost" else "shoot", 90)
        for p in list(self.projectiles):
            p.update(dt, now, self.particles)
        self.projectiles = [p for p in self.projectiles if not p.dead]
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        # round cleared?
        if self.phase == "wave" and self.to_spawn == 0 and not self.waves and self.city_hp > 0:
            bonus = 30 + self.wave_no * 8
            self.money += bonus
            self.phase = "build"
            self.say(f"Wave {self.wave_no} cleared! Bonus +${bonus}. Build, then SPACE for Wave {self.wave_no + 1}.", 5)
            SFX.play("clear")

    # ----- drawing
    def draw(self, surf, fonts, now):
        ox = random.uniform(-self.shake, self.shake) if self.shake else 0
        oy = random.uniform(-self.shake, self.shake) if self.shake else 0
        surf.save_clip() if False else None
        draw_background(surf, now)
        # slot pads
        for i, x in enumerate(SLOT_XS):
            r = pygame.Rect(x - 30, GROUND_Y - 6, 60, 14)
            colour = GOLD if i == self.selected else (255, 255, 255)
            pygame.draw.rect(surf, colour, r, border_radius=5)
            pygame.draw.rect(surf, GREY, r, 1, border_radius=5)
        draw_city(surf, fonts["small"], self.city_hp)
        for s in self.structures.values():
            s.draw(surf, self.selected == s.slot, fonts["small"])
        for w in self.waves:
            w.draw(surf, now)
        for p in self.projectiles:
            p.draw(surf)
        for p in self.particles:
            p.draw(surf)
        if ox or oy:  # cheap shake: blit a shifted copy is overkill; shake is visual via particles/message
            pass
        self.draw_hud(surf, fonts)

    def draw_hud(self, surf, fonts):
        big, mid, small = fonts["big"], fonts["mid"], fonts["small"]
        pygame.draw.rect(surf, (18, 28, 42), (0, 0, WIDTH, 54))
        items = [
            f"Wave: {self.wave_no}" + ("" if self.phase != 'build' else " (next: " + str(self.wave_no + 1) + ")"),
            f"Money: ${self.money}",
            f"City HP: {self.city_hp}/{self.city_max}",
            f"Phase: {'BUILD - press SPACE' if self.phase == 'build' else 'WAVE INCOMING!' if self.phase == 'wave' else 'GAME OVER'}",
            f"Destroyed: {self.kills}",
        ]
        x = 16
        for it in items:
            t = mid.render(it, True, GOLD if "Money" in it else WHITE)
            surf.blit(t, (x, 15))
            x += t.get_width() + 34
        # city hp bar top-right
        pygame.draw.rect(surf, BLACK, (WIDTH - 224, 14, 204, 24))
        pygame.draw.rect(surf, RED, (WIDTH - 222, 16, 200, 20))
        pygame.draw.rect(surf, GREEN, (WIDTH - 222, 16, 200 * self.city_hp / self.city_max, 20))
        # bottom bar
        pygame.draw.rect(surf, (18, 28, 42), (0, HEIGHT - 74, WIDTH, 74))
        lines = [
            "Click a slot, then:  [1] Wall $50    [2] Cannon $100    [3] Frost $120    [U] Upgrade $75    [X] Sell    [R] Repair city $75",
            "SPACE start wave    P pause    M mute all    N music on/off" + ("    *** PAUSED ***" if self.paused else ""),
        ]
        for i, line in enumerate(lines):
            surf.blit(small.render(line, True, WHITE), (16, HEIGHT - 66 + i * 26))
        if self.selected is not None:
            s = self.structures.get(self.selected)
            info = f"Selected slot {self.selected + 1}: " + (f"{s.kind} Lv{s.level} HP {int(s.hp)}/{s.max_hp}" if s else "empty")
            surf.blit(small.render(info, True, GOLD), (880, HEIGHT - 66))
        if self.msg_timer > 0 and self.message:
            t = big.render(self.message, True, WHITE)
            bg = pygame.Rect(WIDTH // 2 - t.get_width() // 2 - 14, 66, t.get_width() + 28, 46)
            pygame.draw.rect(surf, (18, 28, 42), bg, border_radius=8)
            surf.blit(t, (WIDTH // 2 - t.get_width() // 2, 76))
        # mid-game update notification - persistent, never interrupts play
        self.update_available = UPDATE_STATE.get("latest")
        if self.update_available and self.phase != "over":
            note = f"Update v{self.update_available} available! Finish this game, close, then run the launcher to update."
            t = small.render(note, True, BLACK)
            bg = pygame.Rect(WIDTH // 2 - t.get_width() // 2 - 12, 120, t.get_width() + 24, 32)
            pygame.draw.rect(surf, GOLD, bg, border_radius=8)
            pygame.draw.rect(surf, BLACK, bg, 2, border_radius=8)
            surf.blit(t, (WIDTH // 2 - t.get_width() // 2, 126))
        if self.phase == "over":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 10, 20, 185))
            surf.blit(overlay, (0, 0))
            t = big.render("THE CITY HAS FALLEN", True, RED)
            surf.blit(t, (WIDTH // 2 - t.get_width() // 2, 280))
            t2 = mid.render(f"You survived to Wave {self.wave_no} and destroyed {self.kills} tsunami(s).", True, WHITE)
            surf.blit(t2, (WIDTH // 2 - t2.get_width() // 2, 335))
            t3 = mid.render("Press ENTER to play again", True, GOLD)
            surf.blit(t3, (WIDTH // 2 - t3.get_width() // 2, 385))


def slot_at(pos):
    mx, my = pos
    for i, x in enumerate(SLOT_XS):
        if abs(mx - x) <= 42 and GROUND_Y - 165 <= my <= GROUND_Y + 26:
            return i
    return None


def main():
    test_mode = os.environ.get("TSUNAMI_TEST") == "1"
    if test_mode:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    SFX.init()
    MUSIC.init()
    if not test_mode:
        threading.Thread(target=_update_checker_loop, daemon=True).start()
    surf = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(f"Tsunami Defense v{VERSION}")
    clock = pygame.time.Clock()
    fonts = {
        "big": pygame.font.SysFont(None, 34),
        "mid": pygame.font.SysFont(None, 27),
        "small": pygame.font.SysFont(None, 22),
    }
    game = Game()
    # a friendly starting setup hint: pre-select first slot
    game.selected = 0
    frames = 0
    running = True
    while running:
        dt = min(0.05, clock.tick(FPS) / 1000.0)
        now = pygame.time.get_ticks() / 1000.0
        frames += 1
        if test_mode:
            # scripted smoke test: build, start waves, let towers fight
            if frames == 5:
                game.build("cannon")
                game.selected = 1
                game.build("wall")
                game.selected = 2
                game.money += 200
                game.build("frost")
            if frames == 10:
                game.start_wave()
            if frames > 300:
                print(f"SMOKE TEST OK: frames={frames} wave={game.wave_no} "
                      f"city_hp={game.city_hp} money={game.money} waves_alive={len(game.waves)} "
                      f"sfx_enabled={SFX.enabled} sfx_sounds={len(SFX.sounds)} "
                      f"music_enabled={MUSIC.enabled} music_tracks={len(MUSIC.tracks)} music_current={MUSIC.current}")
                running = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                slot = slot_at(event.pos)
                if slot is not None:
                    game.selected = slot
                    SFX.play("click", 50)
            elif event.type == pygame.KEYDOWN:
                if game.phase == "over" and event.key in (pygame.K_RETURN, pygame.K_r):
                    game = Game()
                    game.selected = 0
                    continue
                if event.key == pygame.K_SPACE:
                    game.start_wave()
                elif event.key == pygame.K_1:
                    game.build("wall")
                elif event.key == pygame.K_2:
                    game.build("cannon")
                elif event.key == pygame.K_3:
                    game.build("frost")
                elif event.key == pygame.K_u:
                    game.upgrade_selected()
                elif event.key == pygame.K_x:
                    game.sell_selected()
                elif event.key == pygame.K_r:
                    game.repair()
                elif event.key == pygame.K_p:
                    game.paused = not game.paused
                elif event.key == pygame.K_m:
                    muted = SFX.toggle_mute()
                    MUSIC.muted = muted
                    game.say(f"Sound + music {'OFF' if muted else 'ON'}")
                elif event.key == pygame.K_n:
                    on = MUSIC.toggle_music()
                    game.say(f"Music {'ON' if on else 'OFF'}")
                elif event.key == pygame.K_ESCAPE:
                    running = False
        game.update(dt, now)
        MUSIC.refresh(game.phase, game.paused)
        game.draw(surf, fonts, now)
        pygame.display.flip()
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
