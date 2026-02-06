"""
CLI command: Drive the robot with a USB joystick while viewing video feed.

Designed for EP Engineering Robot (arm + gripper).

Controls:
- Left stick: Forward/backward and strafe left/right  
- Right stick X: Rotate left/right
- D-pad up/down: Arm Y position (up/down)
- D-pad left/right: Arm X position (retract/extend)
- Y button: Arm recenter
- X button: Toggle LED feedback on/off
- Bumpers: Gripper open (RB) / close (LB)
- A button: Speed boost

LED feedback (on by default):
- OFF when not moving
- CYAN when moving
- RED when moving with boost (A button)

Includes simulation mode (--simu) to test controls without robot connection.
Use --record to save teleoperation data in LeRobot format for VLA training.
"""

import click
import cv2
import pygame

from .joystick import Joystick
from .config import MOVEMENT, ARM, ROBOT_VIDEO, LEROBOT
from .lerobot_recorder import LeRobotRecorder
from .telemetry import TelemetryDisplay, setup_telemetry_subscriptions, cleanup_telemetry_subscriptions
from .video import open_webcam
from driver import RobotDriver, SDKDriver, run_simulation


def drive_loop(joystick: Joystick, driver: RobotDriver, mode: str, show_video: bool,
               lerobot_recorder: LeRobotRecorder = None, telemetry_display: TelemetryDisplay = None,
               video_resolution: str = '360p', webcam_cap=None):
    """Main drive loop using abstract driver interface.
    
    Args:
        joystick: Joystick instance
        driver: Robot driver
        mode: 'continuous' or 'step'
        show_video: Whether to show robot video
        lerobot_recorder: Optional LeRobotRecorder for recording mode
        telemetry_display: Optional TelemetryDisplay for real-time telemetry
        video_resolution: Video resolution for window positioning
        webcam_cap: Optional cv2.VideoCapture for USB webcam
    """
    
    # Video window positioning
    VIDEO_WINDOW_NAME = "RoboMaster Drive"
    video_widths = {'360p': 640, '540p': 960, '720p': 1280}
    video_width = video_widths.get(video_resolution, 640)
    window_x = 50
    window_y = 100
    video_positioned = False
    webcam_positioned = False
    
    click.echo(f"\n🚗 Ready to drive! Mode: {mode}")
    click.echo("   Left stick: Move | Right stick X: Rotate")
    click.echo("   D-pad up/down: Arm Y | D-pad left/right: Arm X")
    click.echo("   Y button: Arm recenter | X button: Toggle LED feedback")
    click.echo("   LB: Close gripper | RB: Open gripper | A: Speed boost")
    if lerobot_recorder:
        click.echo("   Back button: Start/Stop recording episode")
    click.echo("   Start button: Quit | Press 'q' or ESC to quit\n")
    
    # LED feedback state
    prev_x_button = False
    led_feedback_enabled = True  # Dynamic LED feedback on by default
    last_led_state = None  # Track: None=off, 'cyan'=moving, 'red'=boost
    
    # Recording state
    prev_back_button = False
    episodes_saved = 0
    
    try:
        while True:
            state = joystick.get_state()
            
            # Speed multiplier (A button for boost)
            speed_mult = MOVEMENT.get('boost_multiplier', 2.0) if state.a else 1.0
            
            # Chassis control
            vx, vy, vz = 0, 0, 0  # Track for recording
            
            if mode == 'continuous':
                # Calculate analog intensity (0-1) based on stick displacement
                left_intensity = max(abs(state.left_x), abs(state.left_y))
                right_intensity = abs(state.right_x)
                
                # Apply analog intensity as multiplier (more push = more speed)
                # Combined with boost button for cumulative effect
                xy_mult = left_intensity * speed_mult
                z_mult = right_intensity * speed_mult
                
                vx = state.left_y * MOVEMENT['continuous_speed_xy'] * xy_mult
                vy = state.left_x * MOVEMENT['continuous_speed_xy'] * xy_mult
                # For rotation: use sign for direction, intensity already in z_mult
                # Stick right (positive) = rotate right (positive vz in SDK)
                rotation_sign = 1 if state.right_x > 0 else (-1 if state.right_x < 0 else 0)
                vz = rotation_sign * MOVEMENT['continuous_speed_z'] * z_mult
                
                if abs(vx) > 0.01 or abs(vy) > 0.01 or abs(vz) > 0.01:
                    driver.drive_speed(vx, vy, vz)
                    
                    # Record movement command
                    if lerobot_recorder:
                        lerobot_recorder.add_command({
                            'move_x': vx,
                            'move_y': vy,
                            'rotate_z': vz
                        })
            
            elif mode == 'step':
                # Only send step command if chassis is ready (previous move completed)
                if driver.is_chassis_ready():
                    if abs(state.left_y) > 0.5 or abs(state.left_x) > 0.5 or abs(state.right_x) > 0.5:
                        x = MOVEMENT['step_forward'] if state.left_y > 0.5 else (-MOVEMENT['step_forward'] if state.left_y < -0.5 else 0)
                        y = MOVEMENT['step_strafe'] if state.left_x > 0.5 else (-MOVEMENT['step_strafe'] if state.left_x < -0.5 else 0)
                        # Invert rotation: stick right = positive z = rotate left in SDK, so negate
                        z = -MOVEMENT['step_rotate'] if state.right_x > 0.5 else (MOVEMENT['step_rotate'] if state.right_x < -0.5 else 0)
                        
                        if x != 0 or y != 0 or z != 0:
                            driver.drive_move(x, y, z, MOVEMENT['speed_xy'], MOVEMENT['speed_z'])
                            
                            # Record step command as velocity equivalent
                            if lerobot_recorder:
                                lerobot_recorder.add_command({
                                    'move_x': x * 10,  # Scale step to approximate velocity
                                    'move_y': y * 10,
                                    'rotate_z': z
                                })
            
            # Arm control (D-pad + Y button)
            arm_x_delta, arm_y_delta = 0, 0
            arm_recenter = False
            
            if driver.is_arm_ready():
                # Y button: recenter arm
                if state.y:
                    driver.arm_recenter()
                    arm_recenter = True
                else:
                    # D-pad: move arm
                    if state.dpad_up:
                        arm_y_delta = ARM['step_y']
                    elif state.dpad_down:
                        arm_y_delta = -ARM['step_y']
                    
                    if state.dpad_right:
                        arm_x_delta = ARM['step_x']
                    elif state.dpad_left:
                        arm_x_delta = -ARM['step_x']
                    
                    if arm_x_delta != 0 or arm_y_delta != 0:
                        driver.arm_move(arm_x_delta, arm_y_delta)
            
            # Record arm commands
            if lerobot_recorder and (arm_x_delta != 0 or arm_y_delta != 0 or arm_recenter):
                lerobot_recorder.add_command({
                    'arm_x': arm_x_delta,
                    'arm_y': arm_y_delta,
                    'arm_recenter': 1 if arm_recenter else 0
                })
            
            # Gripper control - progressive open/close while button held
            gripper_open_power, gripper_close_power = 0, 0
            
            if state.lb:
                driver.gripper_close(power=50)
                gripper_close_power = 50
            elif state.rb:
                driver.gripper_open(power=50)
                gripper_open_power = 50
            else:
                driver.gripper_stop()
            
            # Record gripper commands
            if lerobot_recorder and (gripper_open_power > 0 or gripper_close_power > 0):
                lerobot_recorder.add_command({
                    'gripper_open': gripper_open_power,
                    'gripper_close': gripper_close_power
                })
            
            # LED feedback toggle (X button - edge triggered)
            if state.x and not prev_x_button:
                led_feedback_enabled = not led_feedback_enabled
                if not led_feedback_enabled:
                    driver.led_off()
                    last_led_state = None
                click.echo(f"💡 LED feedback {'ON' if led_feedback_enabled else 'OFF'}")
            prev_x_button = state.x
            
            # Dynamic LED feedback based on movement
            if led_feedback_enabled:
                # Detect if moving (any significant stick input)
                is_moving = (abs(state.left_x) > 0.2 or abs(state.left_y) > 0.2 or 
                            abs(state.right_x) > 0.2)
                is_boost = state.a and is_moving
                
                # Determine target LED state
                if is_boost:
                    target_led = 'red'
                elif is_moving:
                    target_led = 'cyan'
                else:
                    target_led = None  # off
                
                # Only update if state changed
                if target_led != last_led_state:
                    if target_led == 'red':
                        driver.led_on(255, 0, 0)
                    elif target_led == 'cyan':
                        driver.led_on(0, 255, 255)
                    else:
                        driver.led_off()
                    last_led_state = target_led
            
            # Video display (robot camera)
            robot_frame = None
            if show_video:
                img = driver.get_video_frame()
                if img is not None:
                    robot_frame = img.copy()  # Save for recording
                    
                    cv2.putText(img, f"L: ({state.left_x:.1f}, {state.left_y:.1f})", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(img, f"R: ({state.right_x:.1f}, {state.right_y:.1f})", 
                               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    speed_text = f"Mode: {mode}" + (" [BOOST]" if state.a else "")
                    color = (0, 255, 255) if state.a else (0, 255, 0)
                    cv2.putText(img, speed_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    
                    status = driver.get_status()
                    cv2.putText(img, f"Arm: {status.arm_status}", 
                               (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    cv2.putText(img, f"Triggers: L={state.left_trigger:.1f} R={state.right_trigger:.1f}", 
                               (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    gripper_text = "CLOSE" if state.lb else ("OPEN" if state.rb else "-")
                    cv2.putText(img, f"Gripper: {gripper_text}", 
                               (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    # Show recording indicator
                    if lerobot_recorder:
                        if lerobot_recorder.is_recording:
                            # Recording in progress (red)
                            cv2.putText(img, f"REC [{lerobot_recorder.frame_count}]", 
                                       (10, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                            # Draw red circle
                            cv2.circle(img, (160, 205), 8, (0, 0, 255), -1)
                        else:
                            # Ready to record (gray), show episodes count
                            text = f"READY (Episodes: {episodes_saved})"
                            cv2.putText(img, text, (10, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (128, 128, 128), 2)
                    
                    cv2.imshow("RoboMaster Drive", img)
                    
                    # Position video window on first frame
                    if not video_positioned:
                        cv2.moveWindow("RoboMaster Drive", window_x, window_y)
                        video_positioned = True
            
            # Add robot frame to recorder
            if lerobot_recorder and robot_frame is not None:
                lerobot_recorder.add_robot_frame(robot_frame)
            
            # USB Webcam display (if provided)
            webcam_frame = None
            if webcam_cap is not None:
                ret, webcam_img = webcam_cap.read()
                if ret and webcam_img is not None:
                    webcam_frame = webcam_img.copy()  # Save for recording
                    cv2.imshow("USB Webcam", webcam_img)
                    if not webcam_positioned:
                        # Position to the right of robot video
                        cv2.moveWindow("USB Webcam", window_x + video_width + 20, window_y)
                        webcam_positioned = True
            
            # Add webcam frame to recorder
            if lerobot_recorder and webcam_frame is not None:
                lerobot_recorder.add_webcam_frame(webcam_frame)
            
            # Update telemetry display
            if telemetry_display:
                telemetry_display.update()
            
            # Back button: toggle recording (edge triggered)
            if lerobot_recorder and state.back and not prev_back_button:
                if lerobot_recorder.is_recording:
                    # Stop and save episode
                    click.echo("\n💾 Saving episode...")
                    if lerobot_recorder.stop():
                        episodes_saved += 1
                        click.echo(f"✓ Episode {episodes_saved} saved")
                    else:
                        click.echo("⚠️  Episode not saved (dry run or error)")
                else:
                    # Start new episode
                    click.echo("\n🔴 Starting new episode...")
                    lerobot_recorder.start()
            prev_back_button = state.back
            
            # Start button: quit drive
            if state.start:
                click.echo("\n⏹️  Quit (Start button pressed)")
                if lerobot_recorder and lerobot_recorder.is_recording:
                    lerobot_recorder.abort()
                break
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                if lerobot_recorder and lerobot_recorder.is_recording:
                    lerobot_recorder.abort()
                break
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if lerobot_recorder and lerobot_recorder.is_recording:
                        lerobot_recorder.abort()
                    break
                    
    except KeyboardInterrupt:
        if lerobot_recorder and lerobot_recorder.is_recording:
            lerobot_recorder.abort()
    
    finally:
        click.echo("\n🛑 Stopping robot...")
        driver.stop()
        driver.gripper_stop()
        driver.led_off()  # Turn off LEDs on exit
        
        if show_video:
            try:
                cv2.destroyAllWindows()
            except:
                pass
        
        click.echo("✓ Robot stopped")
        if lerobot_recorder:
            click.echo(f"📼 Episodes saved this session: {episodes_saved}")
    
    return episodes_saved


# Get default resolution from config
_default_resolution = ROBOT_VIDEO.get('default_resolution', '360p')
_default_fps = LEROBOT.get('default_fps', 30)
_default_task = LEROBOT.get('default_task', 'do something with Robomaster')


@click.command()
@click.option('--local-ip', '-l', default=None, help='Local IP address')
@click.option('--robot-ip', '-r', default=None, help='Robot IP address')
@click.option('--mode', '-m', default='continuous', 
              type=click.Choice(['continuous', 'step']),
              help='Movement mode: continuous (real-time) or step (discrete)')
@click.option('--resolution', '-res', default=_default_resolution,
              type=click.Choice(['360p', '540p', '720p']),
              help=f'Video resolution (default: {_default_resolution})')
@click.option('--no-video', is_flag=True, help='Disable all video feeds (robot + webcam)')
@click.option('--no-webcam', is_flag=True, help='Disable USB webcam only (robot video still on)')
@click.option('--device', '-d', default=None, type=int,
              help='USB webcam device index (overrides config, e.g., 0 for /dev/video0)')
@click.option('--simu', is_flag=True, help='Simulation mode (no robot connection)')
@click.option('--record', is_flag=True, help='Record teleoperation data in LeRobot format')
@click.option('--task', default=None, 
              help=f'Episode task description (default: "{_default_task}")')
@click.option('--fps', default=None, type=int,
              help=f'Recording FPS (default: {_default_fps})')
@click.option('--dry-run', is_flag=True, help='Print frame info instead of saving (use with --record)')
@click.option('--telemetry', '-t', is_flag=True, 
              help='Show real-time telemetry window (position, velocity, arm, gripper)')
def drive(local_ip, robot_ip, mode, resolution, no_video, no_webcam, device, simu, 
          record, task, fps, dry_run, telemetry):
    """
    Drive the robot with a USB joystick.
    
    Designed for EP Engineering Robot.
    
    \b
    Controls:
    - Left stick: Move forward/backward and strafe
    - Right stick X: Rotate
    - D-pad: Arm control (up/down=Y, left/right=X)
    - Y button: Arm recenter
    - X button: Toggle LED
    - LB/RB: Gripper close/open
    - A: Speed boost
    - Back button: Start/Stop episode recording (when --record)
    
    \b
    Recording (--record):
    Press Back button to start recording an episode. Drive the robot
    to perform a task. Press Back again to stop and save the episode.
    You can record multiple episodes in a single session.
    Press q/ESC to quit (current episode is aborted if recording).
    
    Use --simu for simulation mode without robot connection.
    """
    
    # Initialize joystick
    click.echo("🎮 Initializing joystick...")
    try:
        joystick = Joystick()
        click.echo(f"✓ Joystick detected: {joystick.name}")
        click.echo(f"  Axes: {joystick.num_axes}, Buttons: {joystick.num_buttons}")
    except RuntimeError as e:
        click.echo(f"❌ {e}")
        return
    
    # Simulation mode
    if simu:
        run_simulation(joystick, mode)
        joystick.close()
        return
    
    # Real robot drive mode
    base_driver = SDKDriver()
    lerobot_recorder = None
    webcam_cap = None
    telemetry_display = None
    
    try:
        click.echo("Connecting to robot...")
        base_driver.connect(local_ip, robot_ip)
        click.echo("✓ Connected!")
        
        # Report capabilities
        if base_driver.has_arm:
            click.echo("✓ Robotic arm detected")
        else:
            click.echo("⚠️  No robotic arm detected")
        
        if base_driver.has_gripper:
            click.echo("✓ Gripper detected")
        else:
            click.echo("⚠️  No gripper detected")
        
        # Setup LeRobot recording if requested
        if record:
            recording_fps = fps or _default_fps
            recording_task = task or _default_task
            
            lerobot_recorder = LeRobotRecorder(
                fps=recording_fps,
                task=recording_task,
                dry_run=dry_run
            )
            
            if dry_run:
                click.echo(f"📼 [DRY RUN] Recording mode at {recording_fps} FPS")
            else:
                click.echo(f"📼 Recording mode at {recording_fps} FPS")
            click.echo(f"   Task: {recording_task}")
            click.echo("   Press Back button to start/stop episode recording")
            # Don't auto-start - user will press Back to start first episode
        
        # Start video if enabled
        show_video = not no_video
        if show_video:
            if base_driver.start_video(resolution):
                click.echo(f"📹 Video stream started ({resolution})")
            else:
                click.echo(f"⚠️  Video failed")
                show_video = False
        
        # Setup USB webcam by default (unless --no-video or --no-webcam)
        if not no_video and not no_webcam:
            from .config import WEBCAM
            webcam_device = device if device is not None else WEBCAM.get('device_index', 0)
            click.echo(f"📹 Opening USB webcam (device {webcam_device})...")
            webcam_cap = open_webcam(device)
            if webcam_cap is None:
                click.echo(f"⚠️  Webcam not available at device {webcam_device} (skipping)")
            else:
                actual_width = int(webcam_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(webcam_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                click.echo(f"✓ Webcam opened ({actual_width}x{actual_height})")
        
        # Setup telemetry if requested
        if telemetry:
            from .config import TELEMETRY
            telemetry_display = TelemetryDisplay()
            freq = TELEMETRY.get('frequency', 50)
            click.echo(f"📊 Setting up telemetry ({freq} Hz)...")
            if setup_telemetry_subscriptions(base_driver, telemetry_display, freq):
                click.echo("✓ Telemetry subscriptions active")
            # Get video width for positioning (if video enabled)
            video_width = 0
            if show_video:
                # Map resolution to width: 360p=640, 540p=960, 720p=1280
                video_widths = {'360p': 640, '540p': 960, '720p': 1280}
                video_width = video_widths.get(resolution, 640)
            telemetry_display.start(video_width)
        
        # Run drive loop
        drive_loop(joystick, base_driver, mode, show_video, lerobot_recorder, telemetry_display, 
                   video_resolution=resolution, webcam_cap=webcam_cap)
        
    except RuntimeError as e:
        click.echo(f"❌ {e}")
    
    finally:
        # Cleanup webcam
        if webcam_cap is not None:
            webcam_cap.release()
        
        # Cleanup telemetry
        if telemetry:
            if telemetry_display:
                telemetry_display.stop()
            cleanup_telemetry_subscriptions(base_driver)
        
        base_driver.disconnect()
        joystick.close()
        click.echo("Connection closed.")


if __name__ == '__main__':
    drive()
