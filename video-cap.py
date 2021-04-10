import time
import cv2
import numpy as np

if __name__ == '__main__':

    cam = cv2.VideoCapture(0)
    
    cv2.namedWindow('Display')
    success, img = cam.read()

    while success and cv2.waitKey(1)==-1:
        cv2.imshow('Display', img)
        success, img = cam.read()
    
    cv2.destroyAllWindows()
    cam.release()


