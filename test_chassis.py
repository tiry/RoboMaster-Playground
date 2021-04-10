import os
import unittest
from sim_chassis import Chassis
import pygame

class TestSimChassis(unittest.TestCase):

    def setUp(self):
        pygame.init()
        main_dir = os.path.split(os.path.abspath(__file__))[0]
        img_dir = os.path.join(main_dir, "img")
        self.img = pygame.image.load(os.path.join(img_dir, "Robo-Top-mini.png"))
  
    def test_gobackhome(self):
        
        c = Chassis(self.img, 60)
        c.move(-3,-3,0)
        c.move(6,0,0)
        c.move(0,6,0)
        c.move(-6,0,0)
        c.move(0,-6,0)
        c.move(3,3,0)

        self.assertEqual(0, c.positions[-1].x)
        self.assertEqual(0, c.positions[-1].y)
        self.assertEqual(0, c.positions[-1].z)
    
        

   
if __name__ == "__main__":
  print("running tests")
  unittest.main()
