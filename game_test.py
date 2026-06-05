import pyxel
import random
import math

W, H = 256, 256
TREE_X, TREE_Y = 128, 128
CELL = 16

PREP = 0
FIGHT = 1


def dist(a, b, c, d):
    return math.sqrt((a - c) ** 2 + (b - d) ** 2)


class Enemy:
    def __init__(self, path, hp, speed):
        self.path = path
        self.i = 1
        self.x, self.y = path[0]
        self.hp = hp
        self.max_hp = hp
        self.speed = speed

    def update(self):
        if self.i >= len(self.path):
            return True

        tx, ty = self.path[self.i]
        dx = tx - self.x
        dy = ty - self.y
        d = math.sqrt(dx * dx + dy * dy)

        if d <= self.speed:
            self.x, self.y = tx, ty
            self.i += 1
        else:
            self.x += dx / d * self.speed
            self.y += dy / d * self.speed

        return self.i >= len(self.path)

    def draw(self):
        pyxel.circ(self.x, self.y, 5, 8)
        pyxel.rect(self.x - 6, self.y - 10, 12, 2, 0)
        pyxel.rect(self.x - 6, self.y - 10, 12 * self.hp / self.max_hp, 2, 11)


class Tower:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.range = 45
        self.cooldown = 0

    def update(self, enemies, bullets):
        if self.cooldown > 0:
            self.cooldown -= 1
            return

        target = None
        best = 999

        for e in enemies:
            d = dist(self.x, self.y, e.x, e.y)
            if d < self.range and d < best:
                best = d
                target = e

        if target:
            bullets.append(Bullet(self.x, self.y, target))
            self.cooldown = 25

    def draw(self):
        pyxel.circ(self.x, self.y, 8, 5)
        pyxel.circ(self.x, self.y, 4, 10)
        pyxel.circb(self.x, self.y, self.range, 1)


class Bullet:
    def __init__(self, x, y, target):
        self.x = x
        self.y = y
        self.target = target
        self.speed = 5
        self.damage = 1

    def update(self):
        if self.target.hp <= 0:
            return True

        dx = self.target.x - self.x
        dy = self.target.y - self.y
        d = math.sqrt(dx * dx + dy * dy)

        if d < self.speed:
            self.target.hp -= self.damage
            return True

        self.x += dx / d * self.speed
        self.y += dy / d * self.speed
        return False

    def draw(self):
        pyxel.circ(self.x, self.y, 2, 10)


class Game:
    def __init__(self):
        pyxel.init(W, H, title="Root Blight")
        pyxel.mouse(True)

        self.round = 0
        self.life = 10
        self.gold = 30
        self.state = PREP

        self.paths = []
        self.towers = []
        self.enemies = []
        self.bullets = []

        self.spawn_timer = 0
        self.enemies_to_spawn = 0

        self.new_round()
        pyxel.run(self.update, self.draw)

    def new_round(self):
        self.round += 1
        self.state = PREP
        self.paths = []
        self.towers = []
        self.enemies = []
        self.bullets = []

        branch_count = random.randint(1, 3)
        starts = [
            (0, random.randrange(32, 224, CELL)),
            (240, random.randrange(32, 224, CELL)),
            (random.randrange(32, 224, CELL), 0),
            (random.randrange(32, 224, CELL), 240),
        ]
        random.shuffle(starts)

        for i in range(branch_count):
            self.paths.append(self.make_path(starts[i]))

    def make_path(self, start):
        x, y = start
        path = [(x, y)]

        while x != TREE_X:
            if random.random() < 0.7:
                x += CELL if x < TREE_X else -CELL
            else:
                y += random.choice([-CELL, CELL])
                y = max(16, min(240, y))
            path.append((x, y))

        while y != TREE_Y:
            y += CELL if y < TREE_Y else -CELL
            path.append((x, y))

        path.append((TREE_X, TREE_Y))
        return path

    def start_fight(self):
        self.state = FIGHT
        self.enemies_to_spawn = 5 + self.round * 2
        self.spawn_timer = 0

    def update(self):
        if self.state == PREP:
            self.update_prep()
        else:
            self.update_fight()

    def update_prep(self):
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            x = pyxel.mouse_x // CELL * CELL + CELL // 2
            y = pyxel.mouse_y // CELL * CELL + CELL // 2

            if self.gold >= 10 and not self.on_path(x, y) and dist(x, y, TREE_X, TREE_Y) > 20:
                self.towers.append(Tower(x, y))
                self.gold -= 10

        if pyxel.btnp(pyxel.KEY_SPACE):
            self.start_fight()

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
            tower.update(self.enemies, self.bullets)

        self.bullets = [b for b in self.bullets if not b.update()]

        alive = []
        for e in self.enemies:
            reached = e.update()
            if reached:
                self.life -= 1
            elif e.hp <= 0:
                self.gold += 3
            else:
                alive.append(e)

        self.enemies = alive

        if self.life <= 0:
            self.__init__()

        if self.enemies_to_spawn == 0 and len(self.enemies) == 0:
            self.gold += 10
            self.new_round()

    def on_path(self, x, y):
        for path in self.paths:
            for px, py in path:
                if dist(x, y, px, py) < 12:
                    return True
        return False

    def draw(self):
        pyxel.cls(1)

        for path in self.paths:
            for i in range(len(path) - 1):
                x1, y1 = path[i]
                x2, y2 = path[i + 1]
                pyxel.line(x1, y1, x2, y2, 3)
                pyxel.circ(x1, y1, 4, 3)

        pyxel.circ(TREE_X, TREE_Y, 14, 11)
        pyxel.circ(TREE_X, TREE_Y, 8, 3)
        pyxel.tri(TREE_X - 8, TREE_Y + 14, TREE_X + 8, TREE_Y + 14, TREE_X, TREE_Y + 28, 4)

        for tower in self.towers:
            tower.draw()

        for bullet in self.bullets:
            bullet.draw()

        for enemy in self.enemies:
            enemy.draw()

        self.draw_ui()

    def draw_ui(self):
        pyxel.rect(0, 0, 256, 24, 0)
        pyxel.text(5, 5, f"ROUND {self.round}", 7)
        pyxel.text(80, 5, f"VIE {self.life}", 8)
        pyxel.text(140, 5, f"OR {self.gold}", 10)

        if self.state == PREP:
            pyxel.text(5, 16, "PREP: clic = tour 10 or | ESPACE = lancer", 7)
            pyxel.circb(pyxel.mouse_x, pyxel.mouse_y, 45, 1)
        else:
            pyxel.text(5, 16, "COMBAT: defends l'arbre !", 7)


Game()
