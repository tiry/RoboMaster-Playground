"""
Simple connection test for RoboMaster robot.
Tests WiFi connection and displays video feed from the robot camera.
Press 'q' or ESC to quit.

Configure IP addresses for your network setup.
"""

import time
from robomaster import robot, config
from robomaster import camera
import cv2

# Configure IP addresses - adjust these for your network
LOCAL_IP = "192.168.2.20"   # Your computer's IP on robot's WiFi network
ROBOT_IP = "192.168.2.1"    # Robot's IP address

def main():
    print(f"Initializing RoboMaster connection...")
    print(f"  Local IP: {LOCAL_IP}")
    print(f"  Robot IP: {ROBOT_IP}")
    
    # Configure SDK with our IP addresses
    config.LOCAL_IP_STR = LOCAL_IP
    config.ROBOT_IP_STR = ROBOT_IP
    
    ep_robot = robot.Robot()
    
    try:
        # Connect to robot via WiFi (station mode)
        ep_robot.initialize(conn_type="sta")
        print("✓ Connected to robot!")
        
        # Get robot version info
        ep_version = ep_robot.get_version()
        print(f"✓ Robot Version: {ep_version}")
        
        # Get battery info if available
        try:
            battery = ep_robot.battery
            battery_level = battery.get_battery()
            print(f"✓ Battery Level: {battery_level}%")
        except Exception as e:
            print(f"  Could not get battery info: {e}")
        
        # Start video stream
        ep_camera = ep_robot.camera
        ep_camera.start_video_stream(display=False, resolution=camera.STREAM_360P)
        print("✓ Video stream started!")
        print("\nDisplaying video feed. Press 'q' or ESC to quit.\n")
        
        # Display video feed
        while True:
            img = ep_camera.read_cv2_image(strategy="newest")
            if img is not None:
                cv2.imshow("RoboMaster Video Feed", img)
            
            # Check for quit key
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # 'q' or ESC
                break
        
        # Cleanup
        print("\nClosing video stream...")
        cv2.destroyAllWindows()
        ep_camera.stop_video_stream()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        raise
    
    finally:
        print("Closing robot connection...")
        ep_robot.close()
        print("✓ Connection closed.")

if __name__ == '__main__':
    main()
