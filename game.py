import pyxel 
import random
import math

WIDTH = 256
HEIGHT = 256

class Game:
  def __init__(self):
    pyxel.init(WIDTH, HEIGHT, title="Tower Defense")
    pyxel.run(self.update, self.draw)
    pyxel.mouse(False)
    
  def update(self):
    pass
  
  def draw(self):
    
    pyxel.cls(0)
    pyxel.text(10, 10, "Hello, Pyxel!", 7)

    self.draw_cursor()
    self.draw_menu()
    
  def draw_menu(self):
    pyxel.rect(50, 50, 100, 30, 1)
    pyxel.text(60, 60, "Start Game", 7)
    
  
  def draw_cursor(self):
    x, y = pyxel.mouse_x, pyxel.mouse_y
    pyxel.line(x - 5, y, x + 5, y, 7)
    pyxel.line(x, y - 5, x, y + 5, 7)

    
    
Game()