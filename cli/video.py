"""
CLI command: Open video feed from robot camera or static USB webcam.

By default, shows the robot's camera feed.
Use --static to use an external USB webcam instead.
"""

import click
import cv2
from robomaster import camera
from .connection import connect_robot
from .config import WEBCAM


def run_webcam_video(device_index: int = None):
    """Open video feed from USB webcam.
    
    Args:
        device_index: USB device index (0 = /dev/video0, etc.)
                     If None, uses WEBCAM config value.
    """
    device = device_index if device_index is not None else WEBCAM.get('device_index', 0)
    width = WEBCAM.get('width', 640)
    height = WEBCAM.get('height', 480)
    fps = WEBCAM.get('fps', 30)
    
    click.echo(f"📹 Opening USB webcam (device {device})...")
    
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        click.echo(f"❌ Failed to open webcam at device {device}")
        click.echo(f"   Try: ls /dev/video* to list available devices")
        click.echo(f"   Or: v4l2-ctl --list-devices")
        return
    
    # Configure webcam
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    
    # Get actual settings
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    
    click.echo(f"✓ Webcam opened!")
    click.echo(f"   Resolution: {actual_width}x{actual_height} @ {actual_fps:.0f}fps")
    click.echo("Press 'q' or ESC to quit.\n")
    
    try:
        while True:
            ret, img = cap.read()
            if ret and img is not None:
                cv2.imshow("USB Webcam", img)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
    finally:
        click.echo("\nClosing webcam...")
        cap.release()
        cv2.destroyAllWindows()


def run_robot_video(local_ip, robot_ip, resolution):
    """Open video feed from robot camera."""
    
    # Map resolution to SDK constant
    res_map = {
        '360p': camera.STREAM_360P,
        '540p': camera.STREAM_540P,
        '720p': camera.STREAM_720P,
    }
    stream_res = res_map.get(resolution, camera.STREAM_360P)
    
    with connect_robot(local_ip, robot_ip) as ep_robot:
        ep_camera = ep_robot.camera
        
        click.echo(f"📹 Starting robot video stream ({resolution})...")
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


@click.command()
@click.option('--local-ip', '-l', default=None, help='Local IP address')
@click.option('--robot-ip', '-r', default=None, help='Robot IP address')
@click.option('--resolution', '-res', default='360p', 
              type=click.Choice(['360p', '540p', '720p']),
              help='Video resolution (robot camera only)')
@click.option('--static', is_flag=True, 
              help='Use static USB webcam instead of robot camera')
@click.option('--device', '-d', default=None, type=int,
              help='USB webcam device index (overrides config, e.g., 0 for /dev/video0)')
def video(local_ip, robot_ip, resolution, static, device):
    """
    Open live video feed from the robot camera or USB webcam.
    
    By default, connects to the robot and shows its camera feed.
    Use --static to use an external USB webcam instead.
    
    \b
    Examples:
        robomaster video                    # Robot camera (360p)
        robomaster video -res 720p          # Robot camera (720p)
        robomaster video --static           # USB webcam (device from config)
        robomaster video --static -d 2      # USB webcam at /dev/video2
    """
    
    if static:
        # Use USB webcam
        run_webcam_video(device)
    else:
        # Use robot camera (default)
        run_robot_video(local_ip, robot_ip, resolution)


if __name__ == '__main__':
    video()
