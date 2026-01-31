"""
Capture and display video stream from RoboMaster robot.
Press any key to exit.

Configure IP addresses for your network setup before running.
"""

import time
import cv2
import numpy as np
from robomaster import robot, config, camera

# Configure IP addresses - adjust these for your network
LOCAL_IP = "192.168.2.20"   # Your computer's IP on robot's WiFi network
ROBOT_IP = "192.168.2.1"    # Robot's IP address

if __name__ == '__main__':
    print("Initializing RoboMaster video capture...")
    print(f"  Local IP: {LOCAL_IP}")
    print(f"  Robot IP: {ROBOT_IP}")
    
    # Configure SDK with our IP addresses
    config.LOCAL_IP_STR = LOCAL_IP
    config.ROBOT_IP_STR = ROBOT_IP
    
    ep_robot = robot.Robot()
    
    try:
        ep_robot.initialize(conn_type="sta")
        print("Connected to robot!")
        
        ep_camera = ep_robot.camera
        ep_camera.start_video_stream(display=False, resolution=camera.STREAM_360P)
        print("Video stream started. Press any key to exit.")
        
        cv2.namedWindow('RoboMaster Video')
        
        while True:
            img = ep_camera.read_cv2_image(strategy="newest")
            if img is not None:
                cv2.imshow('RoboMaster Video', img)
            
            if cv2.waitKey(1) != -1:
                break
        
        cv2.destroyAllWindows()
        ep_camera.stop_video_stream()
        
    except Exception as e:
        print(f"Error: {e}")
        raise
        
    finally:
        print("Closing connection...")
        ep_robot.close()
        print("Done.")
