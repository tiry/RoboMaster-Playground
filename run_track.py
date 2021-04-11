import time
from robomaster import robot
from robomaster import camera
import cv2
import numpy as np
import robotrack

if __name__ == '__main__':
    ep_robot = robot.Robot()
    ep_robot.initialize(conn_type="sta")

    ep_version = ep_robot.get_version()
    print("Robot Version: {0}".format(ep_version))

    chassis = ep_robot.chassis

    ep_camera = ep_robot.camera

    ep_camera.start_video_stream(display=False, resolution=camera.STREAM_360P)
    
    #track=robotrack.CircleAround()
    #track=robotrack.TestVelocity()
    track=robotrack.Calibrate()



    track.genMoves()
    track.loadMoves(chassis)

    ep_camera.stop_video_stream()
    
    ep_robot.close()