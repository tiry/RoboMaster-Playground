
from vector import Vector
import pygame
import math

class Chassis:

    TAIL_SIZE=500

    def __init__(self, img, fps):
        self.img=img
        self.pos = Vector(0,0,0)
        self._positions=[]
        self.fps=fps
        self.w=img.get_size()[0]
        self.h=img.get_size()[1]
        self._tail=[]
 
    def _appendToTail(self,v):
        if (len(self._tail)>Chassis.TAIL_SIZE):
            self._tail.pop(0)            
        self._tail.append(v)
        
    def draw(self, screen, center, scale):
        if (len(self._positions)>0):
            self._nextPosition()
        sprite = pygame.transform.rotate(self.img, self.pos.z)
        
        targetVector=Vector(center.x+self.pos.x*scale-self.w/2, center.y-self.pos.y*scale-self.h/2, self.pos.z)
        self._appendToTail(targetVector)
        target = (targetVector.x-self.w/2, targetVector.y-self.h/2)
        new_rect = sprite.get_rect(center = self.img.get_rect(topleft = target).center) 

        self._drawTail(screen)

        screen.blit(sprite, new_rect.topleft)    


    def _drawTail(self, screen):
        l=len(self._tail)
        idx=0
        for t in self._tail:
            idx+=1
            c = 255-(200* (l-idx)/l)
            screen.set_at([int(t.x),int(t.y)], (c,c,c))


    def _getLastPosition(self):
        prev = Vector(self.pos)
        if (len(self._positions)>0): 
            prev = Vector(self._positions[-1])
        return prev

    def move(self,x,y,z, sxy=1, sz=30):
        dxy = Vector(x,y,0).norm()

        ## linear interpolation => need to check actual behavior
        nbSteps = int(max(abs(dxy/(sxy/self.fps)), abs(z/(sz/self.fps))))
        
        print("Steps = {0}".format(nbSteps))
        cp = self._getLastPosition()
        
        for i in range(nbSteps):

            cp = self._getLastPosition()
        
            dx = (1/nbSteps)*x* math.cos(cp.z/360 *(2*math.pi)) + (1/nbSteps)*y* math.cos((cp.z+90)/360 *(2*math.pi))
            dy = (1/nbSteps)*x* math.sin(cp.z/360 *(2*math.pi)) + (1/nbSteps)*y* math.sin((cp.z+90)/360 *(2*math.pi))
        
            cp += Vector(dx,dy,(1/nbSteps)*z)
            print(cp)
            self._positions.append(cp.round(2))

    def _moveOld(self,x,y,z, sxy=1, sz=30):
        dxy = Vector(x,y,0).norm()

        ## linear interpolation => need to check actual behavior
        nbSteps = int(max(abs(dxy/(sxy/self.fps)), abs(z/(sz/self.fps))))
        cp = self._getLastPosition()        
        dx = x* math.cos(cp.z/360 *(2*math.pi)) + y* math.cos((cp.z+90)/360 *(2*math.pi))
        dy = x* math.sin(cp.z/360 *(2*math.pi)) + y* math.sin((cp.z+90)/360 *(2*math.pi))
        target = Vector(dx,dy,z)   
        inc = target * (1/nbSteps)
        
        for x in range(nbSteps):
            cp += inc
            self._positions.append(cp.round(2))

    def _nextPosition(self):
        self.pos = self._positions.pop(0)    

    @property
    def positions(self):
        return self._positions
