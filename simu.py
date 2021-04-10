import pygame
import os
from vector import Vector
from sim_chassis import Chassis
import time
import math

main_dir = os.path.split(os.path.abspath(__file__))[0]
img_dir = os.path.join(main_dir, "img")

class Simulation:

    def __init__(self, screen, chassis):
        self.chassis=chassis
        self.moves=[]
        print(self.__class__.__name__)

    @property
    def name(self):
        return self.__class__.__name__ 

    def init(self):
        self.moves=[]

    def loadMoves(self):
        for mov in self.moves:
            self.chassis.move(mov[0], mov[1], mov[2], mov[3], mov[4])    

    def move(self,x,y,z, sxy=1, sz=30):
        self.moves.append([x,y,z,sxy,sz])

    def renderSimulation(self, screen, center, scale):
        self.chassis.draw(screen, center, scale)

class SimLines(Simulation):

    def genMoves(self):
        self.move(5,00,0,5)
        self.move(-5,00,0,5)
        self.move(0,5,0,5)
        self.move(0,-5,0,5)
    
class SimCircle(Simulation):

    def genMoves(self):
        self._makeCircle(5)
     
    def _makeCircle(self, r, center=Vector(0,0), curPos=Vector(0,0), min_angle=0, max_angle=360):

        self.move(x=-r,y=0,z=0, sxy=2, sz=30)   
    
        ## start circle
        nbSteps=20
        alpha = 360/nbSteps
        ## sin(alpha) = dy / R 
        yStep = round(r*math.sin(alpha/360 *(2*math.pi)),2) 
        speedRatio=4
        
        for i in range(0,nbSteps):
            self.move(x=0,y=-yStep,z=alpha, sxy=speedRatio*yStep, sz=speedRatio*alpha)   
            
        self.move(x=r,y=0,z=0, sxy=2, sz=30)   

class SimBox(Simulation):

    def genMoves(self):
        self.move(-3,-3,0, 2)
        self.move(6,0,0, 2)
        self.move(0,6,0, 2)
        self.move(-6,0,0, 2)
        self.move(0,-6,0, 2)
        self.move(3,3,0, 2)

class SimRBox(Simulation):

    def genMoves(self):
        self.move(-3,3,90+45)
        #self.move(6,0,-90)
        #self.move(0,-6,90)
        #self.move(-6,0,0)
        #self.move(0,-6,0)

class Sim360(Simulation):

    def genMoves(self):
        self.move(0,0,360)

class SimZigZag(Simulation):

    def genMoves(self):
        self.move(0,0,45)
        self.move(4,0,0)
        self.move(0,4,0)
        self.move(-4,0,0)
        self.move(0,-4,0)
        self.move(0,0,-45)
        
def main():
  pygame.init()
  screen = pygame.display.set_mode((800,600))
  pygame.display.set_caption("Robot Simulation")
  clock = pygame.time.Clock()
  fps=60

  chassis_png = pygame.image.load(os.path.join(img_dir, "Robo-Top-mini.png"))
  chassis = Chassis(chassis_png, fps)

  sims = [
            SimCircle(screen, chassis),
            SimBox(screen, chassis),
            SimRBox(screen, chassis),
            Sim360(screen, chassis),
            SimZigZag(screen, chassis),
            SimLines(screen, chassis)
  ]

  curSim={'sim':None, 'idx':0}

  def setCurrentSimulation(idx):
    if idx <0:
        idx=0
    if idx >= len(sims):
        idx = len(sims)-1
    
    curSim['sim'] = sims[idx] 
    curSim['idx'] = idx
    pygame.display.set_caption("Robot Simulation -- " + curSim['sim'].name )
      
  for sim in sims:
    sim.genMoves()
 
  setCurrentSimulation(2)
  
  curSim['sim'].loadMoves()

  center = Vector(400, 300, 0)

  while True:
    clock.tick(fps)
 
    # Handle events
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        return
      elif event.type == pygame.KEYDOWN:
        if event.key == 1073741903:
            curSim['sim'].loadMoves()                        
        elif event.key == 1073741904:
            curSim['sim'].loadMoves()                        
        elif event.key == 1073741906: # UP
            print("prev sim")
            setCurrentSimulation(curSim['idx']-1)
        elif event.key == 1073741905: # DOWN
            print("next sim")
            setCurrentSimulation(curSim['idx']+1)
       
        print (event.key)
 
    screen.fill((0,0,0))
    screen.set_at([center.x,center.y],(255,255,255))
    curSim['sim'].renderSimulation(screen, center, 50 )
    pygame.display.flip()
 
if __name__ == "__main__":
  main()

