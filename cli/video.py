"""
CLI command: Open video feed from robot camera.
"""

import click
import cv2
from robomaster import camera
from .connection import connect_robot


@click.command()
@click.option('--local-ip', '-l', default=None, help='Local IP address')
@click.option('--robot-ip', '-r', default=None, help='Robot IP address')
@click.option('--resolution', '-res', default='360p', 
              type=click.Choice(['360p', '540p', '720p']),
              help='Video resolution')
def video(local_ip, robot_ip, resolution):
    """Open live video feed from the robot camera."""
    
    # Map resolution to SDK constant
    res_map = {
        '360p': camera.STREAM_360P,
        '540p': camera.STREAM_540P,
        '720p': camera.STREAM_720P,
    }
    stream_res = res_map.get(resolution, camera.STREAM_360P)
    
    with connect_robot(local_ip, robot_ip) as ep_robot:
        ep_camera = ep_robot.camera
        
        click.echo(f"📹 Starting video stream ({resolution})...")
        ep_camera.start_video_stream(display=False, resolution=stream_res)
        click.echo("✓ Video stream started!")
        click.echo("Press 'q' or ESC to quit.\n")
        
        try:
            while True:
                img = ep_camera.read_cv2_image(strategy="newest")
                if img is not None:
                    cv2.imshow("RoboMaster Video", img)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:
                    break
        finally:
            click.echo("\nClosing video stream...")
            cv2.destroyAllWindows()
            ep_camera.stop_video_stream()


if __name__ == '__main__':
    video()
