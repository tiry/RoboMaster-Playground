"""
CLI command: Open video feed from robot camera and/or static USB webcam.

By default, shows BOTH robot camera and USB webcam in separate windows.
Use --robot for robot camera only, or --static for webcam only.
"""

import click
import cv2
from robomaster import camera
from .connection import connect_robot
from .config import WEBCAM, ROBOT_VIDEO


def open_webcam(device_index: int = None):
    """Open USB webcam and return capture object.
    
    Args:
        device_index: USB device index (0 = /dev/video0, etc.)
                     If None, uses WEBCAM config value.
    
    Returns:
        cv2.VideoCapture or None if failed
    """
    device = device_index if device_index is not None else WEBCAM.get('device_index', 0)
    width = WEBCAM.get('width', 640)
    height = WEBCAM.get('height', 480)
    fps = WEBCAM.get('fps', 30)
    
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        return None
    
    # Configure webcam
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    
    return cap


def run_webcam_only(device_index: int = None):
    """Open video feed from USB webcam only.
    
    Args:
        device_index: USB device index (0 = /dev/video0, etc.)
    """
    device = device_index if device_index is not None else WEBCAM.get('device_index', 0)
    
    click.echo(f"📹 Opening USB webcam (device {device})...")
    
    cap = open_webcam(device_index)
    if cap is None:
        click.echo(f"❌ Failed to open webcam at device {device}")
        click.echo(f"   Try: ls /dev/video* to list available devices")
        click.echo(f"   Or: v4l2-ctl --list-devices")
        return
    
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


def run_robot_only(local_ip, robot_ip, resolution):
    """Open video feed from robot camera only."""
    
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


def run_dual_video(local_ip, robot_ip, resolution, device_index):
    """Open BOTH robot camera and USB webcam in separate windows."""
    
    # Map resolution to SDK constant
    res_map = {
        '360p': camera.STREAM_360P,
        '540p': camera.STREAM_540P,
        '720p': camera.STREAM_720P,
    }
    stream_res = res_map.get(resolution, camera.STREAM_360P)
    
    # Open webcam first (before robot connection)
    device = device_index if device_index is not None else WEBCAM.get('device_index', 0)
    click.echo(f"📹 Opening USB webcam (device {device})...")
    
    webcam_cap = open_webcam(device_index)
    if webcam_cap is None:
        click.echo(f"⚠️  Webcam not available at device {device}")
        webcam_cap = None
    else:
        actual_width = int(webcam_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(webcam_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        click.echo(f"✓ Webcam opened ({actual_width}x{actual_height})")
    
    # Connect to robot
    with connect_robot(local_ip, robot_ip) as ep_robot:
        ep_camera = ep_robot.camera
        
        click.echo(f"📹 Starting robot video stream ({resolution})...")
        ep_camera.start_video_stream(display=False, resolution=stream_res)
        click.echo("✓ Robot video stream started!")
        click.echo("Press 'q' or ESC to quit.\n")
        
        # Position windows side by side
        video_widths = {'360p': 640, '540p': 960, '720p': 1280}
        robot_width = video_widths.get(resolution, 640)
        
        robot_positioned = False
        webcam_positioned = False
        
        try:
            while True:
                # Robot camera
                robot_img = ep_camera.read_cv2_image(strategy="newest")
                if robot_img is not None:
                    cv2.imshow("RoboMaster Video", robot_img)
                    if not robot_positioned:
                        cv2.moveWindow("RoboMaster Video", 50, 100)
                        robot_positioned = True
                
                # USB Webcam
                if webcam_cap is not None:
                    ret, webcam_img = webcam_cap.read()
                    if ret and webcam_img is not None:
                        cv2.imshow("USB Webcam", webcam_img)
                        if not webcam_positioned:
                            cv2.moveWindow("USB Webcam", 50 + robot_width + 20, 100)
                            webcam_positioned = True
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:
                    break
                    
        finally:
            click.echo("\nClosing video streams...")
            if webcam_cap is not None:
                webcam_cap.release()
            cv2.destroyAllWindows()
            ep_camera.stop_video_stream()


# Get default resolution from config
_default_resolution = ROBOT_VIDEO.get('default_resolution', '360p')


@click.command()
@click.option('--local-ip', '-l', default=None, help='Local IP address')
@click.option('--robot-ip', '-r', default=None, help='Robot IP address')
@click.option('--resolution', '-res', default=_default_resolution, 
              type=click.Choice(['360p', '540p', '720p']),
              help=f'Video resolution for robot camera (default: {_default_resolution})')
@click.option('--static', is_flag=True, 
              help='Use USB webcam ONLY (no robot camera)')
@click.option('--robot', is_flag=True, 
              help='Use robot camera ONLY (no USB webcam)')
@click.option('--device', '-d', default=None, type=int,
              help='USB webcam device index (overrides config, e.g., 0 for /dev/video0)')
def video(local_ip, robot_ip, resolution, static, robot, device):
    """
    Open live video feed from robot camera and/or USB webcam.
    
    \b
    By default, opens BOTH robot camera and USB webcam in separate windows.
    Use --robot for robot camera only, or --static for webcam only.
    
    \b
    Examples:
        robomaster video                    # Both cameras (default)
        robomaster video --robot            # Robot camera only
        robomaster video --static           # USB webcam only
        robomaster video --static -d 2      # USB webcam at /dev/video2
        robomaster video -res 720p          # Both cameras, robot at 720p
    """
    
    # Validate mutually exclusive options
    if static and robot:
        click.echo("❌ Cannot use both --static and --robot. Choose one or neither.")
        return
    
    if static:
        # Webcam only
        run_webcam_only(device)
    elif robot:
        # Robot camera only
        run_robot_only(local_ip, robot_ip, resolution)
    else:
        # Both cameras (default)
        run_dual_video(local_ip, robot_ip, resolution, device)


if __name__ == '__main__':
    video()
