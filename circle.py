import time
from robomaster import robot
from robomaster import camera
import cv2
import numpy as np
import keyboard
import math

def init():
    ep_robot = robot.Robot()
    ep_robot.initialize(conn_type="sta")

    ep_version = ep_robot.get_version()
    print("Robot Version: {0}".format(ep_version))
    return ep_robot

def positionCB(position_info):
    x, y, z = position_info
    print("Robot position: {0},{1},{2}".format(x,y,z)) 


def makeLinePositions():

    pos=[]
    nbSteps=20
    for i in range(1,nbSteps):
        pos.append({'x':0,'y':0.2,'z':0, 'xy_speed':0.5, 'z_speed':0})   
    return pos

def makeCirclePositions(r):

    ## reverse to start position
    pos=[]
    pos.append({'x':-r,'y':0,'z':0, 'xy_speed':0.5, 'z_speed':30})

    ## start circle
    nbSteps=50
    alpha = 360/nbSteps
    ## sin(alpha) = dy / R 
    yStep = round(r*math.sin(alpha/360 *(2*math.pi)),2) 
    speedRatio=4    
    for i in range(1,nbSteps):
        print("step " + str(i))
        pos.append({'x':0,'y':yStep,'z':alpha, 'xy_speed':speedRatio*yStep, 'z_speed':speedRatio*alpha})   

    pos.append({'x':r,'y':0,'z':0, 'xy_speed':0.5, 'z_speed':30})

    return pos

def playPositions(chassis, pos):
    
    i=0
    for p in pos:
        t0=time.time()
        i+=1
        action=chassis.move(x=p['x'],y=p['y'],z=p['z'], xy_speed=p['xy_speed'], z_speed=p['z_speed'])   
        action.wait_for_completed()
        #waitAction(action)
        time.sleep(0.2)
        print("completed move {0} in {1} s".format(i, time.time()-t0) )
        

def makeCircle(chassis, r):

    ## reverse to start position
    print("reverse")
    action=chassis.move(x=-r,y=0,z=0, xy_speed=0.5, z_speed=30)   
    action.wait_for_completed()
    print("reverse_done")
    time.sleep(1)

    ## start circle
    nbSteps=50
    alpha = 360/nbSteps
    ## sin(alpha) = dy / R 
    yStep = round(r*math.sin(alpha/360 *(2*math.pi)),2) 
    print("move " + str(yStep) + " on y and " + str(alpha) + " rotation")       
    speedRatio=4
    
    for i in range(1,nbSteps):
        print("step " + str(i))
        action=chassis.move(x=0,y=yStep,z=alpha, xy_speed=speedRatio*yStep, z_speed=speedRatio*alpha)   
        #action.wait_for_completed()
        waitAction(action)
        #time.sleep(1)
        #if keyboard.is_pressed('q'):
        #    print("Exit")
        #    break
    
    action=chassis.move(x=r,y=0,z=0, xy_speed=0.5, z_speed=30)   
    action.wait_for_completed()
    
   
def waitAction(action):
    while not action.is_completed:
        time.sleep(0.01)

if __name__ == '__main__':
    
    ep_robot = init()
    
    chassis = ep_robot.chassis
    ep_camera = ep_robot.camera

    #chassis.sub_position(cs=0,freq=5, callback=positionCB)

    #makeCircle(chassis, 0.6)
    
    pos = makeCirclePositions(0.6)
    pos = makeLinePositions()
    playPositions(chassis, pos)

    #ep_camera.stop_video_stream()
    
    ep_robot.close()