import pygame
import os
from vector import Vector
from sim_chassis import Chassis
import time
import math
import robotrack
        
def main():

  ## Init 
  pygame.init()
  screen = pygame.display.set_mode((800,600))
  pygame.display.set_caption("Robot Simulation")
  clock = pygame.time.Clock()
  fps=60

  ## Create the Chassis used for simulation
  main_dir = os.path.split(os.path.abspath(__file__))[0]
  img_dir = os.path.join(main_dir, "img")
  chassis_png = pygame.image.load(os.path.join(img_dir, "Robo-Top-mini.png"))
  chassis = Chassis(chassis_png, fps)

  tracks = [
            robotrack.CircleAround(),
            robotrack.DrawBox(),
            robotrack.SimRBox(),
            robotrack.Simple360(),
            robotrack.ZigZag(),
            robotrack.CrossLines(),
            robotrack.TestVelocity(),
            robotrack.Calibrate()
  ]
  
  curTrack={'track':None, 'idx':0}

  def setCurrentTrack(idx):
    if idx <0:
        idx=0
    if idx >= len(tracks):
        idx = len(tracks)-1
    
    curTrack['track'] = tracks[idx] 
    curTrack['idx'] = idx
    pygame.display.set_caption("Robot Simulation -- " + curTrack['track'].name )
      
  for sim in tracks:
    sim.genMoves()
 
  setCurrentTrack(0)
  
  curTrack['track'].loadMoves(chassis)

  center = Vector(400, 300, 0)

  while True:
    clock.tick(fps)
 
    # Handle events
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        return
      elif event.type == pygame.KEYDOWN:
        if event.key == 1073741903:
            curTrack['track'].loadMoves(chassis)                        
        elif event.key == 1073741904:
            curTrack['track'].loadMoves(chassis)                        
        elif event.key == 1073741906: # UP
            print("prev track")
            setCurrentTrack(curTrack['idx']-1)
        elif event.key == 1073741905: # DOWN
            print("next track")
            setCurrentTrack(curTrack['idx']+1)
       
        print (event.key)
 
    screen.fill((0,0,0))
    curTrack['track'].renderSimulation(screen, center, 200, chassis)
    screen.set_at([center.x,center.y],(255,150,150))
    pygame.display.flip()
 
if __name__ == "__main__":
  main()

