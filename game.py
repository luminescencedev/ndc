import pyxel
import random
import math

# --- Dimensions ---
SCREEN = 256          # taille de la fenetre
WORLD = 384           # le monde est plus grand que l'ecran -> camera deplacable
CELL = 16
TREE_X, TREE_Y = 192, 192   # centre du monde

# --- Etats ---
MENU = 0
PREP = 1
FIGHT = 2
GAMEOVER = 3

# --- Zones UI (coordonnees ecran) ---
TOP_H = 18
BAR_Y = 224
BAR_H = SCREEN - BAR_Y

# --- Types de tours ---
# col = couleur du corps, core = couleur du coeur
TOWER_TYPES = [
    {"name": "POUSSE", "cost": 10, "range": 50, "cooldown": 20,
     "damage": 1, "splash": 0,  "slow": 0,  "col": 11, "core": 7},
    {"name": "EPINE",  "cost": 25, "range": 42, "cooldown": 55,
     "damage": 3, "splash": 20, "slow": 0,  "col": 4,  "core": 9},
    {"name": "GIVRE",  "cost": 20, "range": 46, "cooldown": 34,
     "damage": 1, "splash": 0,  "slow": 45, "col": 12, "core": 7},
]


def dist(a, b, c, d):
    return math.sqrt((a - c) ** 2 + (b - d) ** 2)


def in_rect(mx, my, x, y, w, h):
    return x <= mx < x + w and y <= my < y + h


# =====================================================================
class Enemy:
    def __init__(self, path, hp, speed):
        self.path = path
        self.i = 1
        self.x, self.y = path[0]
        self.hp = hp
        self.max_hp = hp
        self.speed = speed
        self.slow = 0          # frames de ralentissement restantes

    def update(self):
        if self.i >= len(self.path):
            return True

        spd = self.speed * (0.45 if self.slow > 0 else 1.0)
        if self.slow > 0:
            self.slow -= 1

        tx, ty = self.path[self.i]
        dx = tx - self.x
        dy = ty - self.y
        d = math.sqrt(dx * dx + dy * dy)

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

        # --- barre de vie stylee ---
        w = 14
        ratio = max(0.0, self.hp / self.max_hp)
        bx = self.x - w // 2
        by = self.y - 11
        pyxel.rect(bx - 1, by - 1, w + 2, 4, 0)
        if ratio > 0.6:
            hc = 11
        elif ratio > 0.3:
            hc = 10
        else:
            hc = 8
        pyxel.rect(bx, by, max(0, int(w * ratio)), 2, hc)


# =====================================================================
class Tower:
    def __init__(self, x, y, kind):
        self.x = x
        self.y = y
        self.kind = kind
        self.level = 1
        self.cooldown = 0

    # --- stats derivees du type et du niveau ---
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
            pyxel.play(2, 4)   # tir tres doux

    def draw(self, selected=False):
        t = self.t
        if selected:
            pyxel.circb(self.x, self.y, self.range, 13)
        pyxel.circ(self.x, self.y, 7, 0)
        pyxel.circ(self.x, self.y, 6, t["col"])
        pyxel.circ(self.x, self.y, 3, t["core"])
        # petits points indiquant le niveau
        for n in range(self.level):
            pyxel.pset(self.x - 2 + n * 2, self.y + 9, 10)


# =====================================================================
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

        dx = self.target.x - self.x
        dy = self.target.y - self.y
        d = math.sqrt(dx * dx + dy * dy)

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


# =====================================================================
class Game:
    def __init__(self):
        pyxel.init(SCREEN, SCREEN, title="Root Blight", fps=60)
        pyxel.mouse(False)
        self.setup_audio()
        pyxel.playm(0, loop=True)
        self.reset()
        self.state = MENU
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------ audio
    def setup_audio(self):
        # melodie douce (pentatonique, ton triangle, volume faible, lente)
        pyxel.sounds[0].set(
            "c3 e3 g3 a3 g3 e3 d3 e3 g3 a3 c4 a3 g3 e3 d3 c3".replace(" ", ""),
            "t", "2", "n", 28)
        # nappe de basse tres calme
        pyxel.sounds[1].set(
            "c2 r r r g2 r r r a2 r r r g2 r r r".replace(" ", ""),
            "t", "1", "f", 28)
        # musique = melodie + basse en boucle
        pyxel.musics[0].set([0], [1], [], [])
        # SFX poser une tour (doux)
        pyxel.sounds[3].set("e3g3", "t", "3", "n", 14)
        # SFX tir (tres discret)
        pyxel.sounds[4].set("a3", "s", "1", "f", 10)
        # SFX ennemi atteint l'arbre
        pyxel.sounds[5].set("c2", "t", "3", "f", 18)

    # ------------------------------------------------ etat global
    def reset(self):
        self.round = 0
        self.life = 12
        self.gold = 35
        self.paths = []
        self.towers = []
        self.enemies = []
        self.bullets = []
        self.fx = []                # effets visuels [x, y, r, vie]
        self.spawn_timer = 0
        self.enemies_to_spawn = 0
        self.cam_x = (WORLD - SCREEN) // 2
        self.cam_y = (WORLD - SCREEN) // 2
        self.build_kind = 0         # type de tour selectionne pour construire
        self.selected = None        # tour selectionnee (pour ameliorer)
        self.new_round()

    # ------------------------------------------------ generation
    def new_round(self):
        self.round += 1
        self.state = PREP
        self.enemies = []
        self.bullets = []
        self.selected = None

        if self.round == 1:
            branch_count = 1
        else:
            branch_count = random.randint(1, min(4, 1 + self.round // 2))

        self.paths = []
        m = CELL
        starts = [
            (0, random.randrange(m * 2, WORLD - m * 2, CELL)),
            (WORLD - CELL, random.randrange(m * 2, WORLD - m * 2, CELL)),
            (random.randrange(m * 2, WORLD - m * 2, CELL), 0),
            (random.randrange(m * 2, WORLD - m * 2, CELL), WORLD - CELL),
        ]
        random.shuffle(starts)
        for i in range(branch_count):
            self.paths.append(self.make_path(starts[i]))

    def make_path(self, start):
        x, y = start
        path = [(x, y)]
        guard = 0
        while x != TREE_X and guard < 200:
            guard += 1
            if random.random() < 0.7:
                x += CELL if x < TREE_X else -CELL
            else:
                y += random.choice([-CELL, CELL])
                y = max(CELL, min(WORLD - CELL, y))
            path.append((x, y))
        while y != TREE_Y and guard < 400:
            guard += 1
            y += CELL if y < TREE_Y else -CELL
            path.append((x, y))
        path.append((TREE_X, TREE_Y))
        return path

    def start_fight(self):
        self.state = FIGHT
        self.enemies_to_spawn = 5 + self.round * 2
        self.spawn_timer = 0

    # ------------------------------------------------ helpers
    def mouse_world(self):
        return pyxel.mouse_x + self.cam_x, pyxel.mouse_y + self.cam_y

    def snap(self, wx, wy):
        gx = wx // CELL * CELL + CELL // 2
        gy = wy // CELL * CELL + CELL // 2
        return gx, gy

    def on_path(self, x, y):
        for path in self.paths:
            for px, py in path:
                if dist(x, y, px, py) < 13:
                    return True
        return False

    def can_build(self, x, y):
        if not (CELL <= x < WORLD - CELL and CELL <= y < WORLD - CELL):
            return False
        if self.on_path(x, y):
            return False
        if dist(x, y, TREE_X, TREE_Y) < 26:
            return False
        for tw in self.towers:
            if dist(x, y, tw.x, tw.y) < CELL:
                return False
        return True

    def tower_at(self, wx, wy):
        for tw in self.towers:
            if dist(wx, wy, tw.x, tw.y) < 10:
                return tw
        return None

    # ------------------------------------------------ update
    def update(self):
        if pyxel.btnp(pyxel.KEY_Q) and pyxel.btn(pyxel.KEY_CTRL):
            pyxel.quit()

        if self.state == MENU:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset()
                self.state = PREP
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
        self.cam_x = max(0, min(WORLD - SCREEN, self.cam_x))
        self.cam_y = max(0, min(WORLD - SCREEN, self.cam_y))

    def update_fx(self):
        for f in self.fx:
            f[3] -= 1
        self.fx = [f for f in self.fx if f[3] > 0]

    def update_prep(self):
        mx, my = pyxel.mouse_x, pyxel.mouse_y

        if pyxel.btnp(pyxel.KEY_SPACE):
            self.start_fight()
            return

        if not pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            return

        # --- clic dans la barre du bas (UI) ---
        if my >= BAR_Y:
            self.click_bottom_bar(mx, my)
            return
        if my < TOP_H:
            return

        # --- clic dans le monde ---
        wx, wy = self.mouse_world()
        tw = self.tower_at(wx, wy)
        if tw:
            self.selected = tw
            return

        gx, gy = self.snap(wx, wy)
        cost = TOWER_TYPES[self.build_kind]["cost"]
        if self.gold >= cost and self.can_build(gx, gy):
            self.towers.append(Tower(gx, gy, self.build_kind))
            self.gold -= cost
            self.selected = None
            pyxel.play(3, 3)

    def click_bottom_bar(self, mx, my):
        # bouton lancer la vague
        if in_rect(mx, my, 196, BAR_Y + 4, 56, 24):
            self.start_fight()
            return

        if self.selected:
            # ameliorer / vendre
            if in_rect(mx, my, 6, BAR_Y + 4, 84, 24):
                cost = self.selected.upgrade_cost()
                if self.gold >= cost and self.selected.level < 3:
                    self.gold -= cost
                    self.selected.level += 1
                return
            if in_rect(mx, my, 96, BAR_Y + 4, 84, 24):
                refund = TOWER_TYPES[self.selected.kind]["cost"] // 2 + (self.selected.level - 1) * 4
                self.gold += refund
                self.towers.remove(self.selected)
                self.selected = None
                return
            self.selected = None
        else:
            # choix du type de tour
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
                pyxel.play(2, 5)
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

    # ------------------------------------------------ draw
    def draw(self):
        if self.state == MENU:
            self.draw_menu()
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
        # grille discrete
        for gx in range(0, WORLD, CELL):
            for gy in range(0, WORLD, CELL):
                pyxel.pset(gx, gy, 0)

        # chemins (terre)
        for path in self.paths:
            for i in range(len(path) - 1):
                x1, y1 = path[i]
                x2, y2 = path[i + 1]
                pyxel.line(x1, y1, x2, y2, 4)
            for px, py in path:
                pyxel.circ(px, py, 4, 4)
                pyxel.pset(px, py, 9)

        # arbre a proteger
        glow = 14 + int(2 * math.sin(pyxel.frame_count * 0.08))
        pyxel.circ(TREE_X, TREE_Y, glow, 3)
        pyxel.circ(TREE_X, TREE_Y, 11, 11)
        pyxel.circ(TREE_X, TREE_Y, 6, 3)
        pyxel.rect(TREE_X - 2, TREE_Y + 8, 4, 12, 4)

        # tours
        for tw in self.towers:
            tw.draw(selected=(tw is self.selected))

        for b in self.bullets:
            b.draw()
        for e in self.enemies:
            e.draw()

        # effets (explosions de l'epine)
        for f in self.fx:
            pyxel.circb(f[0], f[1], f[2] * (5 - f[3]) // 4, f[3] + 1)

        # apercu de construction
        if self.state == PREP and not self.selected:
            wx, wy = self.mouse_world()
            if wy < self.cam_y + TOP_H or wy > self.cam_y + BAR_Y:
                return
            gx, gy = self.snap(wx, wy)
            ok = self.can_build(gx, gy) and self.gold >= TOWER_TYPES[self.build_kind]["cost"]
            t = TOWER_TYPES[self.build_kind]
            ring = 11 if ok else 8
            pyxel.circb(gx, gy, t["range"], ring)
            pyxel.circb(gx, gy, 6, ring)

    # ------------------------------------------------ UI
    def draw_ui(self):
        # barre du haut
        pyxel.rect(0, 0, SCREEN, TOP_H, 0)
        pyxel.rect(0, TOP_H, SCREEN, 1, 5)
        pyxel.text(6, 6, f"VAGUE {self.round}", 7)
        pyxel.text(74, 6, "VIE", 6)
        pyxel.text(92, 6, f"{self.life}", 8)
        for i in range(min(self.life, 12)):
            pyxel.rect(108 + i * 4, 6, 3, 6, 8)
        pyxel.text(SCREEN - 60, 6, f"OR {self.gold}", 10)

        # barre du bas
        pyxel.rect(0, BAR_Y, SCREEN, BAR_H, 0)
        pyxel.rect(0, BAR_Y, SCREEN, 1, 5)

        if self.state == PREP:
            if self.selected:
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
            sel = (i == self.build_kind)
            hover = in_rect(mx, my, x, BAR_Y + 4, 58, 24)
            bg = 5 if (sel or hover) else 0
            pyxel.rect(x, BAR_Y + 4, 58, 24, bg)
            pyxel.rectb(x, BAR_Y + 4, 58, 24, 11 if sel else 13)
            pyxel.circ(x + 9, BAR_Y + 12, 4, t["col"])
            pyxel.circ(x + 9, BAR_Y + 12, 2, t["core"])
            pyxel.text(x + 18, BAR_Y + 8, t["name"], 7)
            col = 10 if self.gold >= t["cost"] else 8
            pyxel.text(x + 18, BAR_Y + 18, f"{t['cost']} or", col)

    def draw_selected_panel(self):
        s = self.selected
        t = s.t
        pyxel.text(8, BAR_Y + 6, f"{t['name']}  Niv.{s.level}", 7)
        pyxel.text(8, BAR_Y + 16, f"deg {s.damage}  portee {s.range}", 6)

        if s.level < 3:
            self.draw_button(96, BAR_Y + 4, 84, 24,
                             f"+ NIV {s.upgrade_cost()}or", 11, 3)
        else:
            pyxel.rect(96, BAR_Y + 4, 84, 24, 0)
            pyxel.rectb(96, BAR_Y + 4, 84, 24, 5)
            pyxel.text(110, BAR_Y + 12, "NIV MAX", 10)

    def draw_button(self, x, y, w, h, label, border, fill):
        mx, my = pyxel.mouse_x, pyxel.mouse_y
        hover = in_rect(mx, my, x, y, w, h)
        pyxel.rect(x, y, w, h, fill if hover else 0)
        pyxel.rectb(x, y, w, h, border)
        tx = x + (w - len(label) * 4) // 2
        pyxel.text(tx, y + h // 2 - 2, label, 7)

    # ------------------------------------------------ ecrans pleins
    def draw_menu(self):
        pyxel.cls(1)
        for i in range(0, SCREEN, 8):
            pyxel.pset(i, (i * 3) % SCREEN, 0)
        cx, cy = SCREEN // 2, 96
        g = 22 + int(3 * math.sin(pyxel.frame_count * 0.06))
        pyxel.circ(cx, cy, g, 3)
        pyxel.circ(cx, cy, 16, 11)
        pyxel.circ(cx, cy, 9, 3)
        pyxel.rect(cx - 2, cy + 14, 4, 20, 4)

        self.center_text(150, "ROOT  BLIGHT", 11)
        self.center_text(164, "defends l'arbre ancien", 6)
        if (pyxel.frame_count // 20) % 2 == 0:
            self.center_text(196, "CLIC ou ESPACE pour jouer", 7)
        self.center_text(232, "fleches/WASD: camera", 5)
        self.center_text(242, "ctrl+Q: quitter", 5)
        self.draw_cursor()

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
