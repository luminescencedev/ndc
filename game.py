import pyxel 
import random
import math

WIDTH = 256
HEIGHT = 256

CELL = 16

TREE_X = 128
TREE_Y = 128

PREP = 0
FIGHT = 1


def dist(a, b, c, d):
    return math.sqrt((a - c) ** 2 + (b - d) ** 2)

class Game:
  def __init__(self):
    pyxel.init(WIDTH, HEIGHT, title="Root Blight")
    pyxel.mouse(True)
    
    self.round = 0  
    self.state = PREP

    self.new_round()
    pyxel.run(self.update, self.draw)

    def update(self):
      if self.state == PREP:
          self.update_prep()
      else:
          self.update_fight()
    
Game()