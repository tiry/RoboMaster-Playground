from vector import Vector
import math

class RoboTrack:

    def __init__(self):
        self.moves=[]
        print(self.__class__.__name__)

    @property
    def name(self):
        return self.__class__.__name__ 

    def init(self):
        self.moves=[]

    def loadMoves(self, chassis):
        for mov in self.moves:
            action = chassis.move(mov[0], mov[1], mov[2], mov[3], mov[4])
            if action is not None:
                action.wait_for_completed()    

    def addMove(self,x,y,z, sxy=1, sz=30):
        self.moves.append([x,y,z,sxy,sz])

    def renderSimulation(self, screen, center, scale, chassis):
        chassis.draw(screen, center, scale)

class CrossLines(RoboTrack):

    def genMoves(self):
        self.addMove(5,00,0,5)
        self.addMove(-5,00,0,5)
        self.addMove(0,5,0,5)
        self.addMove(0,-5,0,5)

class TestVelocity(RoboTrack):

    def genMoves(self):
        self.addMove(1.5,0,90,0.5, 45)
        self.addMove(-1.5,0,-90,0.5, 45)
        
class CircleAround(RoboTrack):

    def genMoves(self):
        self._makeCircle(1)
     
    def _makeCircle(self, r, center=Vector(0,0), curPos=Vector(0,0), min_angle=0, max_angle=360):

        self.addMove(x=-r,y=0,z=0, sxy=2, sz=30)   
    
        ## start circle
        nbSteps=40
        alpha = 360/nbSteps
        ## sin(alpha) = dy / R 
        yStep = round(r*math.sin(alpha/360 *(2*math.pi)),3) 
        speedRatio=4
        
        for i in range(0,nbSteps):
            self.addMove(x=0,y=yStep,z=alpha, sxy=speedRatio*yStep, sz=speedRatio*alpha)   
            
        self.addMove(x=r,y=0,z=0, sxy=2, sz=30)   

class DrawBox(RoboTrack):

    def genMoves(self):
        self.addMove(-2,-2,0, 2)
        self.addMove(4,0,0, 2)
        self.addMove(0,4,0, 2)
        self.addMove(-4,0,0, 2)
        self.addMove(0,-4,0, 2)
        self.addMove(2,2,0, 2)

class Calibrate(RoboTrack):

    def makeCross(self):
        self.addMove(1,0,0)
        self.addMove(-1,0,0)
        self.addMove(0,1,0)
        self.addMove(0,-1,0)
        self.addMove(1,0,-45)
        self.addMove(-1,0,0)
        self.addMove(0,0,90)
        self.addMove(0,1,0)
        self.addMove(0,-1,0)
        self.addMove(0,0,-45)

    def genMoves(self):
        self.makeCross()
        for i in range(4):
            self.addMove(0,0,90)
            self.makeCross()


class SimRBox(RoboTrack):

    def genMoves(self):
        self.addMove(-3,3,90+45)
        #self.move(6,0,-90)
        #self.move(0,-6,90)
        #self.move(-6,0,0)
        #self.move(0,-6,0)

class Simple360(RoboTrack):

    def genMoves(self):
        self.addMove(0,0,360)

class ZigZag(RoboTrack):

    def genMoves(self):
        self.addMove(0,0,45)
        self.addMove(2,0,0)
        self.addMove(0,2,0)
        self.addMove(-2,0,0)
        self.addMove(0,-2,0)
        self.addMove(0,0,-45)