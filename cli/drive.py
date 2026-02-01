"""
CLI command: Drive the robot with a USB joystick while viewing video feed.

Designed for EP Engineering Robot (arm + gripper).

Controls:
- Left stick: Forward/backward and strafe left/right  
- Right stick X: Rotate left/right
- Right stick Y: Arm camera up/down
- Triggers: Arm extend/retract
- Bumpers: Gripper open/close
- A button: Speed boost

Includes simulation mode (--simu) to test controls without robot connection.
"""

import click
import cv2
import pygame

from .joystick import Joystick
from .config import MOVEMENT, ARM
from driver import RobotDriver, SDKDriver, run_simulation


def drive_loop(joystick: Joystick, driver: RobotDriver, mode: str, show_video: bool):
    """Main drive loop using abstract driver interface."""
    
    click.echo(f"\n🚗 Ready to drive! Mode: {mode}")
    click.echo("   Left stick: Move | Right stick X: Rotate")
    click.echo("   Right stick Y: Arm up/down | Triggers: Arm extend/retract")
    click.echo("   LB: Close gripper | RB: Open gripper | A: Speed boost")
    click.echo("   Press 'q' or ESC to quit\n")
    
    try:
        while True:
            state = joystick.get_state()
            
            # Speed multiplier (A button for boost)
            speed_mult = MOVEMENT.get('boost_multiplier', 2.0) if state.a else 1.0
            
            # Chassis control
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
            
            # Arm control
            if driver.is_arm_ready():
                y_delta = 0
                if abs(state.right_y) > 0.3:
                    y_delta = int(state.right_y * ARM['step_y'])
                
                x_delta = 0
                if state.right_trigger > 0.3:
                    x_delta = int(state.right_trigger * ARM['step_x'])
                elif state.left_trigger > 0.3:
                    x_delta = -int(state.left_trigger * ARM['step_x'])
                
                if x_delta != 0 or y_delta != 0:
                    driver.arm_move(x_delta, y_delta)
            
            # Gripper control - progressive open/close while button held
            if state.lb:
                driver.gripper_close(power=50)  # Continuously closes while held
            elif state.rb:
                driver.gripper_open(power=50)   # Continuously opens while held
            else:
                driver.gripper_stop()           # Stop when no button pressed
            
            # Video display
            if show_video:
                img = driver.get_video_frame()
                if img is not None:
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
                    
                    cv2.imshow("RoboMaster Drive", img)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    break
                    
    except KeyboardInterrupt:
        pass
    
    finally:
        click.echo("\n🛑 Stopping robot...")
        driver.stop()
        driver.gripper_stop()
        
        if show_video:
            try:
                cv2.destroyAllWindows()
            except:
                pass
        
        click.echo("✓ Robot stopped")


@click.command()
@click.option('--local-ip', '-l', default=None, help='Local IP address')
@click.option('--robot-ip', '-r', default=None, help='Robot IP address')
@click.option('--mode', '-m', default='continuous', 
              type=click.Choice(['continuous', 'step']),
              help='Movement mode: continuous (real-time) or step (discrete)')
@click.option('--resolution', '-res', default='360p',
              type=click.Choice(['360p', '540p', '720p']),
              help='Video resolution')
@click.option('--no-video', is_flag=True, help='Disable video feed')
@click.option('--simu', is_flag=True, help='Simulation mode (no robot connection)')
def drive(local_ip, robot_ip, mode, resolution, no_video, simu):
    """
    Drive the robot with a USB joystick.
    
    Designed for EP Engineering Robot.
    
    Left stick: Move forward/backward and strafe left/right
    Right stick X: Rotate left/right
    Right stick Y: Arm camera up/down
    
    Use --simu for simulation mode without robot connection.
    
    Press 'q' or ESC to quit.
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
    
    # Real robot mode
    driver = SDKDriver()
    
    try:
        click.echo("Connecting to robot...")
        driver.connect(local_ip, robot_ip)
        click.echo("✓ Connected!")
        
        # Report capabilities
        if driver.has_arm:
            click.echo("✓ Robotic arm detected")
        else:
            click.echo("⚠️  No robotic arm detected")
        
        if driver.has_gripper:
            click.echo("✓ Gripper detected")
        else:
            click.echo("⚠️  No gripper detected")
        
        # Start video if enabled
        show_video = not no_video
        if show_video:
            if driver.start_video(resolution):
                click.echo(f"📹 Video stream started ({resolution})")
            else:
                click.echo(f"⚠️  Video failed")
                show_video = False
        
        # Run drive loop
        drive_loop(joystick, driver, mode, show_video)
        
    except RuntimeError as e:
        click.echo(f"❌ {e}")
    
    finally:
        driver.disconnect()
        joystick.close()
        click.echo("Connection closed.")


if __name__ == '__main__':
    drive()
