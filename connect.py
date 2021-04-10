import time
from robomaster import robot
from robomaster import camera
import cv2
import numpy as np

if __name__ == '__main__':
    ep_robot = robot.Robot()
    ep_robot.initialize(conn_type="sta")

    ep_version = ep_robot.get_version()
    print("Robot Version: {0}".format(ep_version))

    chassis = ep_robot.chassis

    ep_camera = ep_robot.camera

    ep_camera.start_video_stream(display=False, resolution=camera.STREAM_360P)
    action=chassis.move(x=0,y=0,z=180, xy_speed=0.5, z_speed=30)   

    print(action)
    print(dir(action))

    #print(action.wait_for_completed(timeout=0.1))
    #print(action.wait_for_completed(timeout=0.1))
    
    #while not action.wait_for_completed(timeout=0.1):
    #for i in range(0, 30):
    while action._percent < 95:
        img = ep_camera.read_cv2_image(strategy="newest")
        cv2.imshow("Robot", img)
        cv2.waitKey(1)
        #print(img)
        print(action._percent)
        print(action._state)
        output = img.copy()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1.2, 100)
        if circles is not None:
            # convert the (x, y) coordinates and radius of the circles to integers
            circles = np.round(circles[0, :]).astype("int")
            # loop over the (x, y) coordinates and radius of the circles
            for (x, y, r) in circles:
                # draw the circle in the output image, then draw a rectangle
                # corresponding to the center of the circle
                cv2.circle(output, (x, y), r, (0, 255, 0), 4)
                cv2.rectangle(output, (x - 5, y - 5), (x + 5, y + 5), (0, 128, 255), -1)
            # show the output image
            cv2.imshow("output", np.hstack([img, output]))

        time.sleep(0.2)

    action.wait_for_completed()
    
    cv2.destroyAllWindows()


    ep_camera.stop_video_stream()
    
    ep_robot.close()