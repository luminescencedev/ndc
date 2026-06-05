import pyxel
import math

WIDTH = 256
HEIGHT = 256

# Le chemin que suivent les ennemis (liste de points relies par des lignes)
PATH = [(0, 60), (200, 60), (200, 160), (60, 160), (60, 230), (256, 230)]

TOWER_COST = 20
TOWER_RANGE = 40
TOWER_RELOAD = 20   # frames entre deux tirs (30 frames = 1 seconde)
ENEMY_REWARD = 5    # or gagne par ennemi tue


class Enemy:
  def __init__(self, hp, speed):
    self.x, self.y = PATH[0]
    self.step = 1   # prochain point du chemin a atteindre
    self.hp = hp
    self.speed = speed

  def update(self):
    # avance vers le prochain point du chemin
    tx, ty = PATH[self.step]
    dx, dy = tx - self.x, ty - self.y
    dist = math.hypot(dx, dy)
    if dist <= self.speed:
      self.x, self.y = tx, ty
      self.step += 1
      return self.step >= len(PATH)   # True = arrive au bout
    self.x += dx / dist * self.speed
    self.y += dy / dist * self.speed
    return False

  def draw(self):
    pyxel.circ(self.x, self.y, 4, 8)   # rond rouge


class Tower:
  def __init__(self, x, y):
    self.x, self.y = x, y
    self.cooldown = 0

  def update(self, enemies, bullets):
    if self.cooldown > 0:
      self.cooldown -= 1
      return
    # tire sur le premier ennemi a portee
    for e in enemies:
      if math.hypot(e.x - self.x, e.y - self.y) <= TOWER_RANGE:
        bullets.append(Bullet(self.x, self.y, e))
        self.cooldown = TOWER_RELOAD
        break

  def draw(self):
    pyxel.circb(self.x, self.y, TOWER_RANGE, 1)   # cercle de portee
    pyxel.rect(self.x - 4, self.y - 4, 8, 8, 11)  # carre vert


class Bullet:
  def __init__(self, x, y, target):
    self.x, self.y = x, y
    self.target = target

  def update(self):
    # suit sa cible, retourne True quand la balle doit disparaitre
    if self.target.hp <= 0:
      return True
    dx, dy = self.target.x - self.x, self.target.y - self.y
    dist = math.hypot(dx, dy)
    if dist <= 4:
      self.target.hp -= 1
      return True
    self.x += dx / dist * 4
    self.y += dy / dist * 4
    return False

  def draw(self):
    pyxel.circ(self.x, self.y, 1, 10)   # point jaune


class Game:
  def __init__(self):
    pyxel.init(WIDTH, HEIGHT, title="Mini Tower Defense")
    pyxel.load("theme.pyxres")
    pyxel.mouse(True)
    self.reset()
    pyxel.run(self.update, self.draw)

  def reset(self):
    self.gold = 50
    self.lives = 10
    self.wave = 1
    self.spawned = 0    # ennemis deja apparus dans la vague
    self.timer = 0
    self.enemies = []
    self.towers = []
    self.bullets = []
    self.game_over = False

  def update(self):
    if self.game_over:
      if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
        self.reset()
      return

    # clic = poser une tour
    if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and self.gold >= TOWER_COST:
      self.towers.append(Tower(pyxel.mouse_x, pyxel.mouse_y))
      self.gold -= TOWER_COST

    # apparition des ennemis (1 toutes les 30 frames)
    nb_dans_vague = 4 + self.wave * 2
    self.timer += 1
    if self.spawned < nb_dans_vague and self.timer >= 30:
      self.enemies.append(Enemy(2 + self.wave, 1 + self.wave * 0.1))
      self.spawned += 1
      self.timer = 0
    # vague suivante quand tous les ennemis sont morts
    if self.spawned == nb_dans_vague and not self.enemies:
      self.wave += 1
      self.spawned = 0

    for t in self.towers:
      t.update(self.enemies, self.bullets)
    self.bullets = [b for b in self.bullets if not b.update()]

    for e in self.enemies[:]:
      if e.update():   # arrive au bout du chemin
        self.lives -= 1
        self.enemies.remove(e)
      elif e.hp <= 0:  # tue
        self.gold += ENEMY_REWARD
        self.enemies.remove(e)

    if self.lives <= 0:
      self.game_over = True
      pyxel.play(0, 0)   # petit theme de Sans, c'est de circonstance

  def draw(self):
    pyxel.cls(0)
    # le chemin
    for i in range(len(PATH) - 1):
      pyxel.line(*PATH[i], *PATH[i + 1], 4)

    for t in self.towers:
      t.draw()
    for e in self.enemies:
      e.draw()
    for b in self.bullets:
      b.draw()

    # interface
    pyxel.text(5, 5, f"OR: {self.gold}  VIES: {self.lives}  VAGUE: {self.wave}", 7)
    pyxel.text(5, 13, f"CLIC: poser une tour ({TOWER_COST} or)", 6)

    if self.game_over:
      pyxel.text(WIDTH // 2 - 20, HEIGHT // 2, "GAME OVER", 8)
      pyxel.text(WIDTH // 2 - 32, HEIGHT // 2 + 10, "clic pour rejouer", 7)


Game()
