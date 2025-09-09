#!/usr/bin/env python3
"""
Mob Hunters — sprites build (pygbag-ready)
- Adds icons for player, mobs, and animals.
- No assets required: procedural placeholders are auto-drawn.
- If PNGs are present in ./assets, they are used instead (e.g., assets/player.png).
- Keeps: mob cap (25), animals always respawn, Ender Dragon respawns on entering End,
         skeleton arrows, virtual joystick/buttons, async main loop.

Controls
--------
Desktop: WASD to move, E or Left-click to attack, Shift dash
Mobile:  Left stick = move, ATTACK/DASH buttons
1/2/3 switch Overworld/Nether/End. P pause. R restart. Esc quit (desktop).
"""

import os, random, asyncio
from dataclasses import dataclass
from typing import Tuple, List, Optional

import pygame

# --- on-canvas error overlay for web ---
def _draw_error_overlay(screen, lines):
    screen.fill((12, 10, 16))
    font_big = pygame.font.Font(None, 36)
    font_sm  = pygame.font.Font(None, 20)
    title = font_big.render("An error occurred:", True, (255, 210, 210))
    screen.blit(title, (40, 40))
    y = 90
    for ln in lines[-22:]:
        im = font_sm.render(ln, True, (230, 220, 220))
        screen.blit(im, (40, y))
        y += 22
    pygame.display.flip()

# ----------------------------- Config ---------------------------------

WIDTH, HEIGHT = 1000, 640
FPS = 60
TILE = 32

OVERWORLD, NETHER, END = "OVERWORLD", "NETHER", "END"

COL = {
    "bg_over": (30, 36, 46),
    "bg_neth": (35, 16, 16),
    "bg_end":  (18, 18, 26),
    "grid": (50, 58, 70),
    "hud": (245, 245, 245),
    "hp_ok": (65, 220, 120),
    "hp_low": (230, 90, 90),
    "p1": (90, 180, 255),
    "mob": (245, 200, 90),
    "elite": (250, 130, 20),
    "boss": (170, 90, 255),
    "portal_n": (255, 120, 80),
    "portal_e": (180, 160, 255),
    "drop": (240, 230, 80),
    "slash": (255, 255, 255),
    "pack": (90, 230, 120),
    "animal_chicken": (250, 250, 210),
    "animal_pig": (255, 170, 170),
    "animal_cow": (170, 150, 130),
    "arrow": (230, 240, 255),
    "stick_base": (60, 64, 80),
    "stick_nub": (200, 210, 230),
    "btn_bg": (64, 70, 88),
    "btn_fg": (235, 240, 255),
    "btn_border": (120, 130, 150),
    "btn_active": (120, 180, 255),
}

MAX_LIVE_MOBS = 25
MAX_ALIVE_ANIMALS = 7

# ----------------------------- Helpers --------------------------------

def clamp(v, lo, hi): return max(lo, min(hi, v))

def draw_text(surf, text, pos, size=24, color=(255,255,255), center=False):
    font = pygame.font.Font(None, size)
    im = font.render(text, True, color)
    r = im.get_rect()
    if center: r.center = pos
    else: r.topleft = pos
    surf.blit(im, r)
    return r

def is_down(pressed, key_constant) -> int:
    try:
        return 1 if pressed[key_constant] else 0
    except (IndexError, TypeError):
        sc = pygame.key.get_scancode_from_key(key_constant)
        if 0 <= sc < len(pressed): return 1 if pressed[sc] else 0
        return 0

# FIX 1/2: mouse helper safe for pygbag (get_pressed can be empty)
def mouse_left_down() -> bool:
    try:
        return pygame.mouse.get_pressed(num_buttons=3)[0]
    except Exception:
        return False

# ----------------------------- Data -----------------------------------

@dataclass
class Weapon:
    name: str
    dmg: int
    range_px: int
    cooldown_ms: int

SWORD = Weapon("Sword", dmg=28, range_px=85, cooldown_ms=280)
ELITE_SWORD = Weapon("Diamond Sword", dmg=36, range_px=95, cooldown_ms=260)
BOSS_LOOT = Weapon("End Sword", dmg=50, range_px=110, cooldown_ms=240)

@dataclass
class MobKind:
    name: str
    hp: int
    speed: float
    score: int
    color_key: str
    contact_dmg: int

MOB_KINDS_OVER = [
    MobKind("Zombie Chicken Jockey", hp=50, speed=1.6, score=18, color_key="mob",  contact_dmg=9),
    MobKind("Skeleton Spider Jockey", hp=65, speed=1.8, score=24, color_key="elite", contact_dmg=10),
    MobKind("Zombie", hp=45, speed=1.4, score=12, color_key="mob", contact_dmg=8),
    MobKind("Skeleton", hp=42, speed=1.6, score=14, color_key="mob", contact_dmg=9),
    MobKind("Spider", hp=36, speed=2.0, score=16, color_key="mob", contact_dmg=8),
    MobKind("Pigman", hp=60, speed=1.7, score=20, color_key="elite", contact_dmg=11),
]

MOB_KINDS_NETH = [
    MobKind("Wither Skeleton", hp=90, speed=1.9, score=26, color_key="elite", contact_dmg=12),
    MobKind("Blaze", hp=80, speed=1.8, score=24, color_key="elite", contact_dmg=11),
    MobKind("Ghast (mini)", hp=75, speed=1.2, score=30, color_key="elite", contact_dmg=12),
]

BOSS_ENDER = MobKind("Ender Dragon (tiny)", hp=400, speed=1.4, score=250, color_key="boss", contact_dmg=16)

# Animals (peaceful, heal on death)
@dataclass
class AnimalKind:
    name: str
    hp: int
    speed: float
    heal_amount: int
    color: Tuple[int, int, int]

ANIMALS = [
    AnimalKind("Chicken", hp=20, speed=1.6, heal_amount=15, color=COL["animal_chicken"]),
    AnimalKind("Pig",     hp=35, speed=1.2, heal_amount=25, color=COL["animal_pig"]),
    AnimalKind("Cow",     hp=50, speed=1.0, heal_amount=35, color=COL["animal_cow"]),
]

# ------------------------ Sprite / Icon system -------------------------

ICON_FILES = {
    "player": "assets/player.png",
    "Zombie Chicken Jockey": "assets/zombie.png",
    "Skeleton Spider Jockey": "assets/skeleton.png",
    "Zombie": "assets/zombie.png",
    "Skeleton": "assets/skeleton.png",
    "Spider": "assets/spider.png",
    "Pigman": "assets/pigman.png",
    "Wither Skeleton": "assets/wither_skeleton.png",
    "Blaze": "assets/blaze.png",
    "Ghast (mini)": "assets/ghast.png",
    "Ender Dragon (tiny)": "assets/ender_dragon.png",
    "Chicken": "assets/chicken.png",
    "Pig": "assets/pig.png",
    "Cow": "assets/cow.png",
}

def _try_load_png(path: str) -> Optional[pygame.Surface]:
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception:
        return None

def _make_placeholder(kind_name: str, size: Tuple[int,int], main_color=(230,230,230)) -> pygame.Surface:
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(surf, (0,0,0,90), (0,0,w,h), border_radius=8)
    pygame.draw.rect(surf, main_color, (2,2,w-4,h-4), border_radius=7)
    cn = kind_name.lower()
    center = (w//2, h//2)
    if "player" in cn:
        pygame.draw.circle(surf, (80,160,255), center, min(w,h)//3)
    elif "skeleton" in cn:
        pygame.draw.circle(surf, (240,240,240), center, min(w,h)//3)
        pygame.draw.line(surf, (30,30,30), (center[0]-6,center[1]), (center[0]+6,center[1]), 2)
    elif "zombie" in cn or "pigman" in cn:
        pygame.draw.circle(surf, (120,200,120), center, min(w,h)//3)
    elif "spider" in cn:
        pygame.draw.circle(surf, (160,60,180), center, min(w,h)//3)
    elif "blaze" in cn:
        pygame.draw.circle(surf, (255,170,40), center, min(w,h)//3)
    elif "ghast" in cn:
        pygame.draw.circle(surf, (220,220,240), center, min(w,h)//3)
    elif "ender dragon" in cn:
        pygame.draw.circle(surf, (100,60,200), center, min(w,h)//2)
        pygame.draw.circle(surf, (255,240,80), (center[0]+8,center[1]-4), 3)
    elif "chicken" in cn:
        pygame.draw.circle(surf, (250,250,210), center, min(w,h)//3)
    elif "pig" in cn:
        pygame.draw.circle(surf, (255,170,170), center, min(w,h)//3)
    elif "cow" in cn:
        pygame.draw.circle(surf, (170,150,130), center, min(w,h)//3)
    else:
        pygame.draw.circle(surf, (200,200,220), center, min(w,h)//3)
    pygame.draw.rect(surf, (0,0,0,160), (0,0,w,h), width=2, border_radius=8)
    return surf

def make_sprite(name: str, size: Tuple[int,int], fallback_color=(230,230,240)) -> pygame.Surface:
    path = ICON_FILES.get(name, "")
    img = _try_load_png(path)
    if img:
        if img.get_size() != size:
            img = pygame.transform.smoothscale(img, size)
        outline = pygame.Surface((size[0]+4, size[1]+4), pygame.SRCALPHA)
        outline.blit(img, (2,2))
        pygame.draw.rect(outline, (0,0,0,160), outline.get_rect(), 2, border_radius=8)
        return outline
    return _make_placeholder(name, (size[0]+4, size[1]+4), fallback_color)

# ----------------------------- Entities --------------------------------

class Entity:
    def __init__(self, x, y, w, h, color=(255,255,255)):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = color
        self.image: Optional[pygame.Surface] = None  # sprite image centered on rect

class Player(Entity):
    def __init__(self, x, y, color):
        super().__init__(x, y, 26, 26, color)
        self.max_hp = 100
        self.hp = self.max_hp
        self.spd = 3.2
        self.dash_spd = 5.5
        self.weapon = SWORD
        self.last_attack = 0
        self.score = 0
        self.alive = True
        self.slash_timer = 0
        self.slash_radius = 0

    def try_attack(self, targets_rects: List[pygame.Rect]):
        now = pygame.time.get_ticks()
        if now - self.last_attack < self.weapon.cooldown_ms: return []
        center = pygame.Vector2(self.rect.center)
        hits_idx = []
        for i, r in enumerate(targets_rects):
            if r is None: continue
            if center.distance_to(r.center) <= self.weapon.range_px:
                hits_idx.append(i)
        if hits_idx:
            self.last_attack = now
            self.slash_timer = 120
            self.slash_radius = self.weapon.range_px
        return hits_idx

    def move(self, dx, dy, dash=False):
        if not self.alive: return
        vec = pygame.Vector2(dx, dy)
        spd = self.dash_spd if dash else self.spd
        if vec.length_squared() > 0: vec = vec.normalize() * spd
        self.rect.x += int(vec.x); self.rect.y += int(vec.y)
        self.rect.x = clamp(self.rect.x, 4, WIDTH-4-self.rect.w)
        self.rect.y = clamp(self.rect.y, 64, HEIGHT-4-self.rect.h)
        if self.slash_timer > 0:
            self.slash_timer -= 1000 / FPS
            if self.slash_timer < 0: self.slash_timer = 0

class Mob(Entity):
    def __init__(self, kind: MobKind, x, y):
        color = COL[kind.color_key]
        super().__init__(x, y, 24, 24, color)
        self.kind = kind
        self.hp = kind.hp
        self.max_hp = kind.hp
        self.alive = True
        self.knockback = pygame.Vector2(0, 0)
        self.is_archer = ("skeleton" in kind.name.lower())
        self.shots_left = 3 if self.is_archer else 0
        self.last_shot_time = 0
        self.shot_cooldown_ms = 950
        self.shot_range = 380

    def ai(self, target_pos: Tuple[int,int]):
        if not self.alive: return
        dir_vec = pygame.Vector2(target_pos) - self.rect.center
        if dir_vec.length_squared() > 0: dir_vec = dir_vec.normalize() * self.kind.speed
        self.rect.x += int(dir_vec.x + self.knockback.x)
        self.rect.y += int(dir_vec.y + self.knockback.y)
        self.rect.x = clamp(self.rect.x, 4, WIDTH-4-self.rect.w)
        self.rect.y = clamp(self.rect.y, 64, HEIGHT-4-self.rect.h)
        self.knockback *= 0.85
        if self.knockback.length() < 0.2: self.knockback.xy = (0, 0)

    def draw(self, surf):
        if self.image:
            r = self.image.get_rect(center=self.rect.center)
            surf.blit(self.image, r.topleft)
        else:
            pygame.draw.rect(surf, self.color, self.rect, border_radius=6)
        draw_text(surf, self.kind.name, (self.rect.centerx, self.rect.top - 14),
                  size=14, color=(255,255,255), center=True)
        frac = self.hp / max(1, self.max_hp)
        w, h = self.rect.w, 4
        bg = pygame.Rect(self.rect.x, self.rect.top - 8, w, h)
        hp = pygame.Rect(self.rect.x, self.rect.top - 8, int(w * frac), h)
        pygame.draw.rect(surf, (40,40,40), bg)
        pygame.draw.rect(surf, (200,40,40), hp)

class Animal(Entity):
    def __init__(self, kind: AnimalKind, x, y):
        super().__init__(x, y, 22, 22, kind.color)
        self.kind = kind
        self.hp = kind.hp
        self.max_hp = kind.hp
        self.alive = True
        self._dir = pygame.Vector2(random.uniform(-1,1), random.uniform(-1,1))
        if self._dir.length_squared() == 0: self._dir.xy = (1,0)
        self._dir = self._dir.normalize()
        self._change_dir_timer = random.randint(900, 1800)

    def ai(self):
        if not self.alive: return
        self._change_dir_timer -= 1000 / FPS
        if self._change_dir_timer <= 0:
            self._dir = pygame.Vector2(random.uniform(-1,1), random.uniform(-1,1))
            if self._dir.length_squared() == 0: self._dir.xy = (1,0)
            self._dir = self._dir.normalize()
            self._change_dir_timer = random.randint(900, 1800)
        vel = self._dir * self.kind.speed
        self.rect.x += int(vel.x); self.rect.y += int(vel.y)
        if self.rect.left <= 4 or self.rect.right >= WIDTH-4: self._dir.x *= -1
        if self.rect.top <= 64 or self.rect.bottom >= HEIGHT-4: self._dir.y *= -1
        self.rect.x = clamp(self.rect.x, 4, WIDTH-4-self.rect.w)
        self.rect.y = clamp(self.rect.y, 64, HEIGHT-4-self.rect.h)

    def draw(self, surf):
        if self.image:
            r = self.image.get_rect(center=self.rect.center)
            surf.blit(self.image, r.topleft)
        else:
            pygame.draw.rect(surf, self.color, self.rect, border_radius=6)
        draw_text(surf, self.kind.name, (self.rect.centerx, self.rect.top - 14),
                  size=14, color=(230,255,230), center=True)
        frac = self.hp / max(1, self.max_hp)
        w, h = self.rect.w, 3
        bg = pygame.Rect(self.rect.x, self.rect.top - 8, w, h)
        hp = pygame.Rect(self.rect.x, self.rect.top - 8, int(w * frac), h)
        pygame.draw.rect(surf, (40,60,40), bg)
        pygame.draw.rect(surf, (90,220,120), hp)

# ----------------------------- Projectiles --------------------------------

class Arrow:
    def __init__(self, x, y, vx, vy, dmg=12):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(vx, vy)
        self.rect = pygame.Rect(int(x)-3, int(y)-3, 6, 6)
        self.dmg = dmg
        self.alive = True
        self.ttl_ms = 3500
    def update(self, dt_ms):
        if not self.alive: return
        self.pos += self.vel
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self.ttl_ms -= dt_ms
        if self.ttl_ms <= 0: self.alive = False
        if (self.rect.right < 0 or self.rect.left > WIDTH or
            self.rect.bottom < 0 or self.rect.top > HEIGHT):
            self.alive = False
    def draw(self, surf):
        pygame.draw.circle(surf, COL["arrow"], self.rect.center, 3)
        tail = (self.rect.centerx - int(self.vel.x*2), self.rect.centery - int(self.vel.y*2))
        pygame.draw.line(surf, COL["arrow"], self.rect.center, tail, 2)

# ----------------------------- Virtual Controls ---------------------------

class VirtualPad:
    """ On-screen joystick + ATTACK/DASH buttons (works with pygbag touch->mouse). """
    def __init__(self):
        pad_margin = 20
        self.stick_base_r = 64
        self.stick_nub_r = 28
        self.stick_center = pygame.Vector2(pad_margin + self.stick_base_r,
                                           HEIGHT - pad_margin - self.stick_base_r)
        btn_w, btn_h, btn_gap = 120, 56, 16
        right_x = WIDTH - pad_margin - btn_w
        bottom_y = HEIGHT - pad_margin - btn_h
        self.btn_attack = pygame.Rect(right_x, bottom_y - btn_h - btn_gap, btn_w, btn_h)
        self.btn_dash   = pygame.Rect(right_x, bottom_y, btn_w, btn_h)

        self.stick_active = False
        self.nub_pos = self.stick_center.copy()
        self.move_vec = pygame.Vector2(0, 0)

        self.attack_pressed = False
        self.dash_pressed = False
        self._attack_latch = False

    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN:
            mx, my = e.pos
            if pygame.Vector2(mx, my).distance_to(self.stick_center) <= self.stick_base_r + 4:
                self.stick_active = True; self._update_stick(mx, my); return
            if self.btn_attack.collidepoint(mx, my):
                self.attack_pressed = True; self._attack_latch = True; return
            if self.btn_dash.collidepoint(mx, my):
                self.dash_pressed = True; return
        elif e.type == pygame.MOUSEBUTTONUP:
            mx, my = e.pos
            if self.stick_active:
                self.stick_active = False
                self.nub_pos.update(self.stick_center)
                self.move_vec.update(0,0)
            if self.btn_dash.collidepoint(mx, my): self.dash_pressed = False
            if self.btn_attack.collidepoint(mx, my): self.attack_pressed = False
        elif e.type == pygame.MOUSEMOTION:
            mx, my = e.pos
            if self.stick_active: self._update_stick(mx, my)

    def _update_stick(self, mx, my):
        v = pygame.Vector2(mx, my) - self.stick_center
        if v.length() > self.stick_base_r: v.scale_to_length(self.stick_base_r)
        self.nub_pos = self.stick_center + v
        if v.length() < 8: self.move_vec.update(0,0)
        else: self.move_vec = v.normalize()

    def consume_attack_tap(self) -> bool:
        if self._attack_latch:
            self._attack_latch = False
            return True
        return False

    def draw(self, surf):
        pygame.draw.circle(surf, COL["stick_base"], self.stick_center, self.stick_base_r)
        pygame.draw.circle(surf, (20, 22, 28), self.stick_center, self.stick_base_r, width=3)
        pygame.draw.circle(surf, COL["stick_nub"], self.nub_pos, self.stick_nub_r)
        pygame.draw.circle(surf, (50, 60, 70), self.nub_pos, self.stick_nub_r, width=2)
        for rect, label, active in [
            (self.btn_attack, "ATTACK", self.attack_pressed),
            (self.btn_dash,   "DASH",   self.dash_pressed),
        ]:
            pygame.draw.rect(surf, COL["btn_active"] if active else COL["btn_bg"], rect, border_radius=10)
            pygame.draw.rect(surf, COL["btn_border"], rect, width=3, border_radius=10)
            draw_text(surf, label, rect.center, 24, COL["btn_fg"], center=True)

# ----------------------------- Game ------------------------------------

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Mob Hunters — Sprites (Mobile/Web)")
        # FIX 3: avoid DOUBLEBUF for pygbag; plain set_mode like the old good build
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        self.theme = OVERWORLD
        self.prev_theme = self.theme
        self.spawn_timer = 0
        self.spawn_interval_ms = 1000

        self.animal_spawn_timer = 0
        self.animal_spawn_interval_ms = 3500

        self.portal_n = pygame.Rect(10, 70, 26, 120)
        self.portal_e = pygame.Rect(WIDTH-36, 70, 26, 120)

        self.p1 = Player(x=WIDTH//2-20, y=HEIGHT//2, color=COL["p1"])
        self.p1.image = make_sprite("player", (26,26), (200,220,255))

        self.mobs: List[Mob] = []
        self.animals: List[Animal] = []
        self.weapon_drops: List[Tuple[pygame.Rect, Weapon]] = []
        self.health_packs: List[Tuple[pygame.Rect, int]] = []

        self.projectiles: List[Arrow] = []

        self.paused = False
        self.round_over = False
        self.end_boss_alive = False

        self.running = True
        self.vpad = VirtualPad()

    # ---------- Spawning ----------

    def live_mob_count(self) -> int:
        return sum(1 for m in self.mobs if m.alive)

    def current_pool(self):
        if self.theme == OVERWORLD: return MOB_KINDS_OVER
        if self.theme == NETHER: return MOB_KINDS_NETH + [random.choice(MOB_KINDS_OVER)]
        return MOB_KINDS_OVER

    def _place_sprite_for_mob(self, mob: Mob):
        size = (64,64) if mob.kind.color_key == "boss" else (24,24)
        mob.image = make_sprite(mob.kind.name, size)

    def spawn_mob(self):
        if self.live_mob_count() >= MAX_LIVE_MOBS:
            return
        pool = self.current_pool()
        kind = random.choice(pool)
        side = random.choice(["top","bottom","left","right"])
        if side == "top": x, y = random.randint(40, WIDTH-40), 72
        elif side == "bottom": x, y = random.randint(40, WIDTH-40), HEIGHT-40
        elif side == "left": x, y = 40, random.randint(80, HEIGHT-40)
        else: x, y = WIDTH-60, random.randint(80, HEIGHT-40)
        mob = Mob(kind, x, y)
        self._place_sprite_for_mob(mob)
        self.mobs.append(mob)

    def spawn_animal(self):
        if sum(1 for a in self.animals if a.alive) >= MAX_ALIVE_ANIMALS:
            return
        kind = random.choice(ANIMALS)
        x = random.randint(60, WIDTH-80)
        y = random.randint(100, HEIGHT-80)
        a = Animal(kind, x, y)
        a.image = make_sprite(kind.name, (22,22))
        self.animals.append(a)

    def spawn_boss(self):
        self.end_boss_alive = True
        b = Mob(BOSS_ENDER, WIDTH//2-80, 120)
        b.rect.size = (64,64)
        self._place_sprite_for_mob(b)
        self.mobs.append(b)

    # ---------- Combat / Damage ----------

    def apply_damage(self, dmg_target, dmg_amount, src_center):
        if not getattr(dmg_target, "alive", False): return
        dmg_target.hp -= dmg_amount
        if hasattr(dmg_target, "rect"):
            kb_dir = pygame.Vector2(dmg_target.rect.center) - pygame.Vector2(src_center)
            if kb_dir.length_squared() == 0: kb_dir.xy = (1, 0)
            kb = kb_dir.normalize() * 4.2
            dmg_target.rect.x += int(kb.x); dmg_target.rect.y += int(kb.y)
        if dmg_target.hp <= 0:
            dmg_target.alive = False
            if isinstance(dmg_target, Mob) and dmg_target.kind.color_key == "boss":
                self.end_boss_alive = False

    def hunter_melee(self):
        targets_rects: List[Optional[pygame.Rect]] = []
        index_to_obj: List[object] = []
        for m in self.mobs:
            if m.alive: targets_rects.append(m.rect); index_to_obj.append(m)
        for a in self.animals:
            if a.alive: targets_rects.append(a.rect); index_to_obj.append(a)
        hits_idx = self.p1.try_attack(targets_rects)
        for idx in hits_idx:
            obj = index_to_obj[idx]
            if isinstance(obj, Mob):
                self.apply_damage(obj, self.p1.weapon.dmg, self.p1.rect.center)
                if not obj.alive:
                    self.p1.score += obj.kind.score
                    if obj.kind.color_key != "boss":
                        if random.random() < (0.10 if obj.kind.color_key == "elite" else 0.05):
                            rect = pygame.Rect(obj.rect.centerx-8, obj.rect.centery-8, 16, 16)
                            self.weapon_drops.append((rect, ELITE_SWORD))
                    else:
                        rect = pygame.Rect(obj.rect.centerx-10, obj.rect.centery-10, 20, 20)
                        self.weapon_drops.append((rect, BOSS_LOOT))
            elif isinstance(obj, Animal):
                self.apply_damage(obj, self.p1.weapon.dmg, self.p1.rect.center)
                if not obj.alive:
                    rect = pygame.Rect(obj.rect.centerx-8, obj.rect.centery-8, 18, 18)
                    self.health_packs.append((rect, obj.kind.heal_amount))

    def mobs_damage_p1_on_touch(self, mob_entity: Mob):
        if not (mob_entity.alive and self.p1.alive): return
        if mob_entity.rect.colliderect(self.p1.rect):
            self.apply_damage(self.p1, mob_entity.kind.contact_dmg, mob_entity.rect.center)
            if self.p1.hp <= 0: self.p1.alive = False; self.round_over = True

    # ---------- Healing ----------

    def try_pick_health(self, who: Player):
        for i, (r, amount) in list(enumerate(self.health_packs)):
            if who.alive and who.rect.colliderect(r):
                who.hp = clamp(who.hp + amount, 0, who.max_hp)
                self.health_packs.pop(i)

    # ---------- Archery ----------

    def try_skeleton_shoot(self, m: Mob, now_ms: int):
        if not (m.is_archer and m.shots_left > 0 and self.p1.alive): return
        dist = pygame.Vector2(m.rect.center).distance_to(self.p1.rect.center)
        if dist > m.shot_range: return
        if now_ms - m.last_shot_time < m.shot_cooldown_ms: return
        m.last_shot_time = now_ms; m.shots_left -= 1
        origin = pygame.Vector2(m.rect.center); target = pygame.Vector2(self.p1.rect.center)
        dirv = (target - origin)
        if dirv.length_squared() == 0: dirv.xy = (1, 0)
        dirv = dirv.normalize() * 5.0
        self.projectiles.append(Arrow(origin.x, origin.y, dirv.x, dirv.y, dmg=12))

    def update_projectiles(self, dt):
        for i, pr in list(enumerate(self.projectiles)):
            if not pr.alive: self.projectiles.pop(i); continue
            pr.update(dt)
            if not pr.alive: self.projectiles.pop(i); continue
            if self.p1.alive and pr.rect.colliderect(self.p1.rect):
                self.apply_damage(self.p1, pr.dmg, pr.rect.center)
                pr.alive = False; self.projectiles.pop(i)
                if self.p1.hp <= 0: self.round_over = True

    # ---------- Draw ----------

    def draw_bg(self):
        bg = {"OVERWORLD": "bg_over", "NETHER": "bg_neth", "END": "bg_end"}[self.theme]
        self.screen.fill(COL[bg])
        for x in range(0, WIDTH, TILE):
            pygame.draw.line(self.screen, COL["grid"], (x, 64), (x, HEIGHT), 1)
        for y in range(64, HEIGHT, TILE):
            pygame.draw.line(self.screen, COL["grid"], (0, y), (WIDTH, y), 1)
        pygame.draw.rect(self.screen, (22, 22, 25), (0, 0, WIDTH, 60))
        draw_text(self.screen, f"Mob Hunters — Theme: {self.theme}", (12, 12), 24, COL["hud"])
        draw_text(self.screen, f"Score: {self.p1.score}", (12, 34), 22, COL["hud"])
        pygame.draw.rect(self.screen, COL["portal_n"], self.portal_n, border_radius=6)
        draw_text(self.screen, "N", self.portal_n.center, 20, (0,0,0), center=True)
        pygame.draw.rect(self.screen, COL["portal_e"], self.portal_e, border_radius=6)
        draw_text(self.screen, "E", self.portal_e.center, 20, (0,0,0), center=True)

    def draw_bar(self, x, y, w, h, frac, color_ok, color_low, label=None):
        frac = clamp(frac, 0, 1)
        col = color_ok if frac > 0.35 else color_low
        pygame.draw.rect(self.screen, (40, 40, 48), (x, y, w, h), border_radius=5)
        pygame.draw.rect(self.screen, col, (x+2, y+2, int((w-4)*frac), h-4), border_radius=5)
        if label: draw_text(self.screen, label, (x, y-12), 14, (220,220,230))

    # ---------- Theme transitions ----------

    def _handle_theme_transitions(self):
        if self.theme != self.prev_theme:
            if self.prev_theme == END and self.theme != END:
                self.end_boss_alive = False
                self.mobs = [m for m in self.mobs if m.kind.color_key != "boss"]
            if self.theme == END:
                self.end_boss_alive = False
                self.mobs = [m for m in self.mobs if m.kind.color_key != "boss"]
                self.spawn_boss()
            self.prev_theme = self.theme

    # ---------- Update / Render / Events ----------

    def restart(self): __class__.__init__(self)

    def update(self, dt):
        if self.paused or self.round_over: return
        pressed = pygame.key.get_pressed()

        # Movement: keyboard or virtual stick
        k_dx = is_down(pressed, pygame.K_d) - is_down(pressed, pygame.K_a)
        k_dy = is_down(pressed, pygame.K_s) - is_down(pressed, pygame.K_w)
        k_dash = bool(is_down(pressed, pygame.K_LSHIFT) or is_down(pressed, pygame.K_RSHIFT))
        v_dx, v_dy = self.vpad.move_vec.x, self.vpad.move_vec.y
        v_dash = self.vpad.dash_pressed
        dx, dy = (v_dx, v_dy) if (abs(v_dx)+abs(v_dy) > 0) else (k_dx, k_dy)
        self.p1.move(dx, dy, dash=(v_dash or k_dash))

        # Attack inputs (FIX 1/2)
        mouse_attack = mouse_left_down()
        key_attack = is_down(pressed, pygame.K_e) == 1
        touch_attack = self.vpad.consume_attack_tap()
        if mouse_attack or key_attack or touch_attack:
            self.hunter_melee()

        # Portals
        if self.p1.rect.colliderect(self.portal_n): self.theme = NETHER
        if self.p1.rect.colliderect(self.portal_e): self.theme = END
        self._handle_theme_transitions()

        # Spawns
        self.spawn_timer += dt
        interval = self.spawn_interval_ms
        if self.theme == NETHER: interval = int(interval * 0.85)
        if self.theme == END:    interval = int(interval * 0.90)
        if self.spawn_timer >= interval:
            self.spawn_timer = 0; self.spawn_mob()

        self.animal_spawn_timer += dt
        if self.animal_spawn_timer >= self.animal_spawn_interval_ms:
            self.animal_spawn_timer = 0; self.spawn_animal()

        # AI, arrows
        now_ms = pygame.time.get_ticks()
        for m in self.mobs:
            if not m.alive: continue
            m.ai(self.p1.rect.center)
            self.mobs_damage_p1_on_touch(m)
            self.try_skeleton_shoot(m, now_ms)

        for a in self.animals:
            if not a.alive: continue
            a.ai()

        # Loot
        for i, (r, wpn) in list(enumerate(self.weapon_drops)):
            if self.p1.rect.colliderect(r):
                self.p1.weapon = wpn; self.weapon_drops.pop(i)

        self.try_pick_health(self.p1)
        self.update_projectiles(dt)

        # Cleanup
        self.mobs = [m for m in self.mobs if m.alive]
        self.animals = [a for a in self.animals if a.alive]

    def render(self):
        self.draw_bg()

        for rect, _ in self.weapon_drops:
            pygame.draw.rect(self.screen, COL["drop"], rect, border_radius=4)
        for rect, _ in self.health_packs:
            pygame.draw.rect(self.screen, COL["pack"], rect, border_radius=4)
            cx, cy = rect.center
            pygame.draw.line(self.screen, (20,60,30), (cx-5, cy), (cx+5, cy), 2)
            pygame.draw.line(self.screen, (20,60,30), (cx, cy-5), (cx, cy+5), 2)

        for pr in self.projectiles:
            if pr.alive: pr.draw(self.screen)

        for m in self.mobs:
            if m.alive: m.draw(self.screen)

        for a in self.animals:
            if a.alive: a.draw(self.screen)

        if self.p1.alive:
            if self.p1.image:
                r = self.p1.image.get_rect(center=self.p1.rect.center)
                self.screen.blit(self.p1.image, r.topleft)
            else:
                pygame.draw.rect(self.screen, (240,240,255), self.p1.rect, border_radius=6)
            pygame.draw.rect(self.screen, COL["p1"], self.p1.rect.inflate(4,4), width=2, border_radius=8)
            if self.p1.slash_timer > 0:
                pygame.draw.circle(self.screen, COL["slash"], self.p1.rect.center, int(self.p1.slash_radius), 2)

        self.draw_bar(220, 16, 260, 16, self.p1.hp / self.p1.max_hp, COL["hp_ok"], COL["hp_low"], "P1 HP")
        draw_text(self.screen, f"Weapon: {self.p1.weapon.name}", (500, 14), 18, COL["hud"])
        draw_text(self.screen, f"Live mobs: {self.live_mob_count()}/{MAX_LIVE_MOBS}", (720, 14), 18, COL["hud"])
        draw_text(self.screen, f"Animals: {sum(1 for a in self.animals if a.alive)}/{MAX_ALIVE_ANIMALS}", (720, 34), 18, COL["hud"])

        draw_text(self.screen,
                  "Mobile: left stick + ATTACK/DASH | Desktop: WASD + E/Click, Shift dash",
                  (12, HEIGHT-26), 18, (230,230,235))

        if self.paused:
            draw_text(self.screen, "PAUSED", (WIDTH//2, HEIGHT//2-20), 48, (255,255,255), center=True)
            draw_text(self.screen, "Press P to resume", (WIDTH//2, HEIGHT//2+20), 24, (230,230,230), center=True)

        if self.round_over:
            draw_text(self.screen, "You Died!", (WIDTH//2, HEIGHT//2-60), 50, (255,240,240), center=True)
            draw_text(self.screen, f"Final Score: {self.p1.score}", (WIDTH//2, HEIGHT//2-12), 30, (255,255,255), center=True)
            draw_text(self.screen, "Press R to restart", (WIDTH//2, HEIGHT//2+34), 24, (240,240,240), center=True)

        self.vpad.draw(self.screen)
        pygame.display.flip()

    def handle_events(self):
        for e in pygame.event.get():
            self.vpad.handle_event(e)
            if e.type == pygame.QUIT:
                self.running = False
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: self.running = False
                if e.key == pygame.K_p: self.paused = not self.paused
                if e.key == pygame.K_r and self.round_over: self.restart()
                if e.key == pygame.K_1: self.theme = OVERWORLD; self._handle_theme_transitions()
                if e.key == pygame.K_2: self.theme = NETHER;    self._handle_theme_transitions()
                if e.key == pygame.K_3: self.theme = END;       self._handle_theme_transitions()

# ----------------------------- Main (async) ----------------------------

async def main():
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    game = Game()

    # visible loading frame (helps confirm the canvas is alive)
    game.screen.fill((10, 10, 14))
    draw_text(game.screen, "Loading Mob Hunters…", (WIDTH//2, HEIGHT//2), 36, (230,230,240), center=True)
    pygame.display.flip()

    while game.running:
        dt = game.clock.tick(FPS)
        try:
            game.handle_events()
            game.update(dt)
            game.render()
        except Exception:
            import traceback
            tb = traceback.format_exc().splitlines()
            print("\n".join(tb))
            _draw_error_overlay(game.screen, tb)
        await asyncio.sleep(0)

    pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())
