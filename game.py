import pyxel
import random
import math

SCREEN = 256
WORLD = 384
CELL = 16
TREE_X, TREE_Y = WORLD // 2, WORLD // 2
FIELD_PAD = 3 * CELL
FIELD_MIN = -FIELD_PAD
FIELD_MAX = WORLD + FIELD_PAD
EMPTY = 2 * CELL

MENU = 0
PREP = 1
FIGHT = 2
GAMEOVER = 3
SETTINGS = 4

TOP_H = 18
BAR_Y = 224
BAR_H = SCREEN - BAR_Y

TOWER_TYPES = [
    {"name": "POUSSE", "cost": 10, "range": 50, "cooldown": 20,
     "damage": 1, "splash": 0,  "slow": 0,  "col": 11, "core": 7},
    {"name": "EPINE",  "cost": 25, "range": 42, "cooldown": 55,
     "damage": 3, "splash": 20, "slow": 0,  "col": 4,  "core": 9},
    {"name": "GIVRE",  "cost": 20, "range": 46, "cooldown": 34,
     "damage": 1, "splash": 0,  "slow": 45, "col": 12, "core": 7},
]


def dist(a, b, c, d):
    return math.hypot(a - c, b - d)


def in_rect(mx, my, x, y, w, h):
    return x <= mx < x + w and y <= my < y + h


class Enemy:
    def __init__(self, path, hp, speed):
        self.path = path
        self.i = 1
        self.x, self.y = path[0]
        self.hp = hp
        self.max_hp = hp
        self.speed = speed
        self.slow = 0

    def update(self):
        if self.i >= len(self.path):
            return True
        spd = self.speed * (0.45 if self.slow > 0 else 1.0)
        if self.slow > 0:
            self.slow -= 1
        tx, ty = self.path[self.i]
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d <= spd:
            self.x, self.y = tx, ty
            self.i += 1
        else:
            self.x += dx / d * spd
            self.y += dy / d * spd
        return self.i >= len(self.path)

    def draw(self):
        col = 12 if self.slow > 0 else 8
        pyxel.circb(self.x, self.y, 5, 0)
        pyxel.circ(self.x, self.y, 4, col)
        pyxel.pset(self.x - 1, self.y - 1, 7)
        w = 14
        ratio = max(0.0, self.hp / self.max_hp)
        bx, by = self.x - w // 2, self.y - 11
        pyxel.rect(bx - 1, by - 1, w + 2, 4, 0)
        hc = 11 if ratio > 0.6 else 10 if ratio > 0.3 else 8
        pyxel.rect(bx, by, max(0, int(w * ratio)), 2, hc)


class Tower:
    def __init__(self, x, y, kind):
        self.x = x
        self.y = y
        self.kind = kind
        self.level = 1
        self.cooldown = 0

    @property
    def t(self):
        return TOWER_TYPES[self.kind]

    @property
    def range(self):
        return self.t["range"] + (self.level - 1) * 8

    @property
    def damage(self):
        return self.t["damage"] + (self.level - 1)

    @property
    def fire_rate(self):
        return max(8, self.t["cooldown"] - (self.level - 1) * 6)

    def upgrade_cost(self):
        return self.t["cost"] + self.level * 8

    def update(self, game):
        if self.cooldown > 0:
            self.cooldown -= 1
            return
        target = None
        best = 99999
        for e in game.enemies:
            d = dist(self.x, self.y, e.x, e.y)
            if d < self.range and d < best:
                best = d
                target = e
        if target:
            game.bullets.append(Bullet(self.x, self.y, target, self, game))
            self.cooldown = self.fire_rate
            game.sfx(2, 4)

    def draw(self, selected=False):
        t = self.t
        if selected:
            pyxel.circb(self.x, self.y, self.range, 13)
        pyxel.circ(self.x, self.y, 7, 0)
        pyxel.circ(self.x, self.y, 6, t["col"])
        pyxel.circ(self.x, self.y, 3, t["core"])
        for n in range(self.level):
            pyxel.pset(self.x - 2 + n * 2, self.y + 9, 10)


class Bullet:
    def __init__(self, x, y, target, tower, game):
        self.x = x
        self.y = y
        self.target = target
        self.tower = tower
        self.game = game
        self.speed = 6

    def update(self):
        if self.target.hp <= 0:
            return True
        dx, dy = self.target.x - self.x, self.target.y - self.y
        d = math.hypot(dx, dy)
        if d < self.speed:
            self.hit()
            return True
        self.x += dx / d * self.speed
        self.y += dy / d * self.speed
        return False

    def hit(self):
        t = self.tower.t
        dmg = self.tower.damage
        self.target.hp -= dmg
        if t["slow"] > 0:
            self.target.slow = t["slow"]
        if t["splash"] > 0:
            for e in self.game.enemies:
                if e is not self.target and dist(self.x, self.y, e.x, e.y) < t["splash"]:
                    e.hp -= dmg
            self.game.fx.append([self.x, self.y, t["splash"], 8])

    def draw(self):
        pyxel.circ(self.x, self.y, 2, self.tower.t["core"])


class Game:
    def __init__(self):
        pyxel.init(SCREEN, SCREEN, title="Root Blight", fps=60)
        pyxel.mouse(False)
        self.music_on = True
        self.sfx_on = True
        self.setup_audio()
        pyxel.playm(0, loop=True)
        self.reset()
        self.state = MENU
        pyxel.run(self.update, self.draw)

    def sfx(self, ch, snd):
        if self.sfx_on:
            pyxel.play(ch, snd)

    def toggle_music(self):
        self.music_on = not self.music_on
        if self.music_on:
            pyxel.playm(0, loop=True)
        else:
            pyxel.stop(0)
            pyxel.stop(1)

    def setup_audio(self):
        pyxel.sounds[0].set("c3e3g3a3g3e3d3e3g3a3c4a3g3e3d3c3", "t", "2", "n", 28)
        pyxel.sounds[1].set("c2rrrg2rrra2rrrg2rrr", "t", "1", "f", 28)
        pyxel.musics[0].set([0], [1], [], [])
        pyxel.sounds[3].set("e3g3", "t", "3", "n", 14)
        pyxel.sounds[4].set("a3", "s", "1", "f", 10)
        pyxel.sounds[5].set("c2", "t", "3", "f", 18)

    def reset(self):
        self.round = 0
        self.life = 12
        self.gold = 35
        self.paths = []
        self.towers = []
        self.enemies = []
        self.bullets = []
        self.fx = []
        self.spawn_timer = 0
        self.enemies_to_spawn = 0
        self.cam_x = (WORLD - SCREEN) // 2
        self.cam_y = (WORLD - SCREEN) // 2
        self.build_kind = 0
        self.selected = None
        self.moving = None
        self.new_round()

    def new_round(self):
        self.round += 1
        self.state = PREP
        self.enemies = []
        self.bullets = []
        self.selected = None
        self.moving = None
        if self.round == 1:
            branch_count = 1
        else:
            branch_count = random.randint(1, min(4, 1 + self.round // 2))
        self.paths = []
        lo = FIELD_MIN + 2 * CELL
        hi = FIELD_MAX - 2 * CELL
        starts = [
            (FIELD_MIN, random.randrange(lo, hi, CELL)),
            (FIELD_MAX, random.randrange(lo, hi, CELL)),
            (random.randrange(lo, hi, CELL), FIELD_MIN),
            (random.randrange(lo, hi, CELL), FIELD_MAX),
        ]
        random.shuffle(starts)
        for i in range(branch_count):
            self.paths.append(self.make_path(starts[i]))

    def make_path(self, start):
        x, y = start
        path = [(x, y)]
        guard = 0
        while x != TREE_X and guard < 400:
            guard += 1
            if random.random() < 0.7:
                x += CELL if x < TREE_X else -CELL
            else:
                y += random.choice([-CELL, CELL])
                y = max(FIELD_MIN, min(FIELD_MAX, y))
            path.append((x, y))
        while y != TREE_Y and guard < 800:
            guard += 1
            y += CELL if y < TREE_Y else -CELL
            path.append((x, y))
        path.append((TREE_X, TREE_Y))
        return path

    def start_fight(self):
        self.state = FIGHT
        self.enemies_to_spawn = 5 + self.round * 2
        self.spawn_timer = 0

    def mouse_world(self):
        return pyxel.mouse_x + self.cam_x, pyxel.mouse_y + self.cam_y

    def snap(self, wx, wy):
        return wx // CELL * CELL + CELL // 2, wy // CELL * CELL + CELL // 2

    def on_path(self, x, y):
        for path in self.paths:
            for px, py in path:
                if dist(x, y, px, py) < 13:
                    return True
        return False

    def can_build(self, x, y, ignore=None):
        if not (FIELD_MIN <= x <= FIELD_MAX and FIELD_MIN <= y <= FIELD_MAX):
            return False
        if self.on_path(x, y):
            return False
        if dist(x, y, TREE_X, TREE_Y) < 26:
            return False
        for tw in self.towers:
            if tw is not ignore and dist(x, y, tw.x, tw.y) < CELL:
                return False
        return True

    def tower_at(self, wx, wy):
        for tw in self.towers:
            if dist(wx, wy, tw.x, tw.y) < 10:
                return tw
        return None

    def update(self):
        if pyxel.btnp(pyxel.KEY_Q) and pyxel.btn(pyxel.KEY_CTRL):
            pyxel.quit()
        if self.state == MENU:
            self.update_menu()
        elif self.state == SETTINGS:
            self.update_settings()
        elif self.state == GAMEOVER:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self.state = PREP
        else:
            self.update_camera()
            if self.state == PREP:
                self.update_prep()
            else:
                self.update_fight()
            self.update_fx()

    def update_menu(self):
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.reset()
            self.state = PREP
            return
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if in_rect(mx, my, 88, 158, 80, 20):
                self.reset()
                self.state = PREP
            elif in_rect(mx, my, 88, 184, 80, 20):
                self.state = SETTINGS

    def update_settings(self):
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            self.state = MENU
            return
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if in_rect(mx, my, 110, 134, 40, 12):
                self.toggle_music()
            elif in_rect(mx, my, 110, 150, 40, 12):
                self.sfx_on = not self.sfx_on
            elif in_rect(mx, my, 88, 208, 80, 20):
                self.state = MENU

    def update_camera(self):
        spd = 4
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            self.cam_x -= spd
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            self.cam_x += spd
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            self.cam_y -= spd
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            self.cam_y += spd
        self.cam_x = max(FIELD_MIN - EMPTY, min(FIELD_MAX + EMPTY - SCREEN, self.cam_x))
        self.cam_y = max(FIELD_MIN - EMPTY - TOP_H, min(FIELD_MAX + EMPTY + BAR_H - SCREEN, self.cam_y))

    def update_fx(self):
        for f in self.fx:
            f[3] -= 1
        self.fx = [f for f in self.fx if f[3] > 0]

    def update_prep(self):
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        if self.moving is not None:
            if pyxel.btnp(pyxel.KEY_ESCAPE) or pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
                self.selected = self.moving
                self.moving = None
            elif pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and TOP_H <= my < BAR_Y:
                gx, gy = self.snap(*self.mouse_world())
                if self.can_build(gx, gy, ignore=self.moving):
                    self.moving.x, self.moving.y = gx, gy
                    self.selected = self.moving
                    self.moving = None
                    self.sfx(3, 3)
            return
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.start_fight()
            return
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            self.selected = None
            return
        if not pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            return
        if my >= BAR_Y:
            self.click_bottom_bar(mx, my)
            return
        if my < TOP_H:
            return
        wx, wy = self.mouse_world()
        tw = self.tower_at(wx, wy)
        if tw:
            self.selected = tw
            return
        if self.selected is not None:
            self.selected = None
            return
        gx, gy = self.snap(wx, wy)
        cost = TOWER_TYPES[self.build_kind]["cost"]
        if self.gold >= cost and self.can_build(gx, gy):
            self.towers.append(Tower(gx, gy, self.build_kind))
            self.gold -= cost
            self.selected = None
            self.sfx(3, 3)

    def click_bottom_bar(self, mx, my):
        if in_rect(mx, my, 196, BAR_Y + 4, 56, 24):
            self.start_fight()
            return
        if self.selected:
            s = self.selected
            if s.level < 3 and in_rect(mx, my, 6, BAR_Y + 15, 58, 11):
                cost = s.upgrade_cost()
                if self.gold >= cost:
                    self.gold -= cost
                    s.level += 1
                return
            if in_rect(mx, my, 68, BAR_Y + 15, 58, 11):
                self.moving = s
                self.selected = None
                return
            if in_rect(mx, my, 130, BAR_Y + 15, 58, 11):
                self.gold += TOWER_TYPES[s.kind]["cost"] // 2 + (s.level - 1) * 4
                self.towers.remove(s)
                self.selected = None
                return
            self.selected = None
        else:
            for i in range(3):
                if in_rect(mx, my, 6 + i * 62, BAR_Y + 4, 58, 24):
                    self.build_kind = i
                    return

    def update_fight(self):
        self.spawn_timer += 1
        if self.spawn_timer >= 35 and self.enemies_to_spawn > 0:
            path = random.choice(self.paths)
            hp = 2 + self.round // 2
            speed = 0.7 + self.round * 0.04
            self.enemies.append(Enemy(path, hp, speed))
            self.enemies_to_spawn -= 1
            self.spawn_timer = 0
        for tower in self.towers:
            tower.update(self)
        self.bullets = [b for b in self.bullets if not b.update()]
        alive = []
        for e in self.enemies:
            if e.update():
                self.life -= 1
                self.sfx(2, 5)
            elif e.hp <= 0:
                self.gold += 3
            else:
                alive.append(e)
        self.enemies = alive
        if self.life <= 0:
            self.state = GAMEOVER
            return
        if self.enemies_to_spawn == 0 and not self.enemies:
            self.gold += 12
            self.new_round()

    def draw(self):
        if self.state == MENU:
            self.draw_menu()
            return
        if self.state == SETTINGS:
            self.draw_settings()
            return
        pyxel.cls(1)
        pyxel.camera(self.cam_x, self.cam_y)
        self.draw_world()
        pyxel.camera()
        self.draw_ui()
        if self.state == GAMEOVER:
            self.draw_gameover()
        self.draw_cursor()

    def draw_world(self):
        for gx in range(FIELD_MIN, FIELD_MAX + CELL, CELL):
            for gy in range(FIELD_MIN, FIELD_MAX + CELL, CELL):
                pyxel.pset(gx, gy, 0)
        for path in self.paths:
            for i in range(len(path) - 1):
                x1, y1 = path[i]
                x2, y2 = path[i + 1]
                pyxel.line(x1, y1, x2, y2, 4)
            for px, py in path:
                pyxel.circ(px, py, 4, 4)
                pyxel.pset(px, py, 9)
        glow = 14 + int(2 * math.sin(pyxel.frame_count * 0.08))
        pyxel.circ(TREE_X, TREE_Y, glow, 3)
        pyxel.circ(TREE_X, TREE_Y, 11, 11)
        pyxel.circ(TREE_X, TREE_Y, 6, 3)
        pyxel.rect(TREE_X - 2, TREE_Y + 8, 4, 12, 4)
        for tw in self.towers:
            tw.draw(selected=(tw is self.selected))
        for b in self.bullets:
            b.draw()
        for e in self.enemies:
            e.draw()
        for f in self.fx:
            pyxel.circb(f[0], f[1], f[2] * (5 - f[3]) // 4, f[3] + 1)
        if self.state == PREP:
            wx, wy = self.mouse_world()
            if not (self.cam_y + TOP_H <= wy <= self.cam_y + BAR_Y):
                return
            gx, gy = self.snap(wx, wy)
            if self.moving is not None:
                ok = self.can_build(gx, gy, ignore=self.moving)
                rng = self.moving.range
            elif not self.selected:
                ok = self.can_build(gx, gy) and self.gold >= TOWER_TYPES[self.build_kind]["cost"]
                rng = TOWER_TYPES[self.build_kind]["range"]
            else:
                return
            ring = 11 if ok else 8
            pyxel.circb(gx, gy, rng, ring)
            pyxel.circb(gx, gy, 6, ring)

    def draw_ui(self):
        pyxel.rect(0, 0, SCREEN, TOP_H, 0)
        pyxel.rect(0, TOP_H, SCREEN, 1, 5)
        pyxel.text(6, 6, f"VAGUE {self.round}", 7)
        pyxel.text(74, 6, "VIE", 6)
        pyxel.text(92, 6, f"{self.life}", 8)
        for i in range(min(self.life, 12)):
            pyxel.rect(108 + i * 4, 6, 3, 6, 8)
        pyxel.text(SCREEN - 60, 6, f"OR {self.gold}", 10)
        pyxel.rect(0, BAR_Y, SCREEN, BAR_H, 0)
        pyxel.rect(0, BAR_Y, SCREEN, 1, 5)
        if self.state == PREP:
            if self.moving is not None:
                pyxel.text(8, BAR_Y + 8, "DEPLACEMENT", 11)
                pyxel.text(8, BAR_Y + 18, "clic: poser | clic droit/ECHAP: annuler", 6)
            elif self.selected:
                self.draw_selected_panel()
            else:
                self.draw_build_panel()
            self.draw_button(196, BAR_Y + 4, 56, 24, "VAGUE", 11, 3)
        else:
            left = self.enemies_to_spawn + len(self.enemies)
            pyxel.text(8, BAR_Y + 8, "COMBAT - defends l'arbre !", 7)
            pyxel.text(8, BAR_Y + 18, f"ennemis restants : {left}", 6)

    def draw_build_panel(self):
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        for i, t in enumerate(TOWER_TYPES):
            x = 6 + i * 62
            sel = i == self.build_kind
            hover = in_rect(mx, my, x, BAR_Y + 4, 58, 24)
            pyxel.rect(x, BAR_Y + 4, 58, 24, 5 if (sel or hover) else 0)
            pyxel.rectb(x, BAR_Y + 4, 58, 24, 11 if sel else 13)
            pyxel.circ(x + 9, BAR_Y + 12, 4, t["col"])
            pyxel.circ(x + 9, BAR_Y + 12, 2, t["core"])
            pyxel.text(x + 18, BAR_Y + 8, t["name"], 7)
            pyxel.text(x + 18, BAR_Y + 18, f"{t['cost']} or", 10 if self.gold >= t["cost"] else 8)

    def draw_selected_panel(self):
        s = self.selected
        t = s.t
        pyxel.text(6, BAR_Y + 4, f"{t['name']} Niv.{s.level}  deg{s.damage} por{s.range}", 7)
        if s.level < 3:
            self.draw_button(6, BAR_Y + 15, 58, 11, f"+NIV {s.upgrade_cost()}", 11, 3)
        else:
            pyxel.rectb(6, BAR_Y + 15, 58, 11, 5)
            pyxel.text(20, BAR_Y + 17, "NIV MAX", 10)
        self.draw_button(68, BAR_Y + 15, 58, 11, "DEPLACER", 12, 3)
        self.draw_button(130, BAR_Y + 15, 58, 11, "VENDRE", 8, 3)

    def draw_button(self, x, y, w, h, label, border, fill):
        hover = in_rect(pyxel.mouse_x, pyxel.mouse_y, x, y, w, h)
        pyxel.rect(x, y, w, h, fill if hover else 0)
        pyxel.rectb(x, y, w, h, border)
        pyxel.text(x + (w - len(label) * 4) // 2, y + h // 2 - 2, label, 7)

    def draw_menu(self):
        pyxel.cls(1)
        for i in range(0, SCREEN, 8):
            pyxel.pset(i, (i * 3) % SCREEN, 0)
        cx, cy = SCREEN // 2, 78
        glow = 22 + int(3 * math.sin(pyxel.frame_count * 0.06))
        pyxel.circ(cx, cy, glow, 3)
        pyxel.circ(cx, cy, 16, 11)
        pyxel.circ(cx, cy, 9, 3)
        pyxel.rect(cx - 2, cy + 14, 4, 20, 4)
        self.center_text(124, "ROOT  BLIGHT", 11)
        self.center_text(138, "defends l'arbre ancien", 6)
        self.draw_button(88, 158, 80, 20, "JOUER", 11, 3)
        self.draw_button(88, 184, 80, 20, "REGLAGES", 13, 3)
        self.center_text(244, "ctrl+Q: quitter", 5)
        self.draw_cursor()

    def draw_settings(self):
        pyxel.cls(1)
        for i in range(0, SCREEN, 8):
            pyxel.pset(i, (i * 5) % SCREEN, 0)
        self.center_text(14, "REGLAGES", 11)
        pyxel.text(28, 34, "COMMANDES", 10)
        lines = [
            ("Clic gauche", "placer / choisir une tour"),
            ("Fleches / WASD", "deplacer la camera"),
            ("ESPACE", "lancer la vague"),
            ("Clic sur tour", "ameliorer / vendre"),
            ("ECHAP", "retour au menu"),
            ("Ctrl + Q", "quitter le jeu"),
        ]
        y = 46
        for key, desc in lines:
            pyxel.text(30, y, key, 7)
            pyxel.text(124, y, desc, 6)
            y += 11
        pyxel.text(28, 120, "AUDIO", 10)
        self.draw_toggle_box(110, 134, self.music_on, "Musique")
        self.draw_toggle_box(110, 150, self.sfx_on, "Effets")
        self.draw_button(88, 208, 80, 20, "RETOUR", 11, 3)
        self.center_text(236, "ECHAP ou clic RETOUR", 5)
        self.draw_cursor()

    def draw_toggle_box(self, x, y, on, label):
        pyxel.text(30, y + 3, label, 7)
        hover = in_rect(pyxel.mouse_x, pyxel.mouse_y, x, y, 40, 12)
        col = 11 if on else 8
        pyxel.rect(x, y, 40, 12, 5 if hover else 0)
        pyxel.rectb(x, y, 40, 12, col)
        txt = "ON" if on else "OFF"
        pyxel.text(x + (40 - len(txt) * 4) // 2, y + 3, txt, col)

    def draw_gameover(self):
        pyxel.rect(0, 96, SCREEN, 64, 0)
        pyxel.rectb(0, 96, SCREEN, 64, 8)
        self.center_text(112, "L'ARBRE EST TOMBE", 8)
        self.center_text(126, f"tu as tenu {self.round} vagues", 7)
        if (pyxel.frame_count // 20) % 2 == 0:
            self.center_text(144, "CLIC pour rejouer", 6)

    def center_text(self, y, s, col):
        pyxel.text((SCREEN - len(s) * 4) // 2, y, s, col)

    def draw_cursor(self):
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        pyxel.line(mx - 5, my, mx + 5, my, 7)
        pyxel.line(mx, my - 5, mx, my + 5, 7)
        pyxel.pset(mx, my, 8)


Game()
