"""
CLI command: Drive the robot with a USB joystick while viewing video feed.

Left stick: Forward/backward and strafe left/right
Right stick: Rotate left/right and gimbal/arm up/down

Includes simulation mode (--simu) to test controls without robot connection.
"""

import click
import cv2
import pygame
import time
import math
import os
from .config import (
    JOYSTICK_AXES, JOYSTICK_BUTTONS, DEADZONE,
    MOVEMENT, GIMBAL, ARM, apply_deadzone
)


def init_joystick():
    """Initialize pygame and joystick."""
    pygame.init()
    pygame.joystick.init()
    
    if pygame.joystick.get_count() == 0:
        raise RuntimeError("No joystick detected! Please connect a controller.")
    
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    
    return joystick


def get_joystick_state(joystick):
    """Read current joystick state and apply deadzone."""
    pygame.event.pump()  # Process events
    
    # Get axis values with deadzone
    left_x = apply_deadzone(joystick.get_axis(JOYSTICK_AXES['left_x']))
    left_y = apply_deadzone(joystick.get_axis(JOYSTICK_AXES['left_y']))
    right_x = apply_deadzone(joystick.get_axis(JOYSTICK_AXES['right_x']))
    right_y = apply_deadzone(joystick.get_axis(JOYSTICK_AXES['right_y']))
    
    return {
        'left_x': left_x,    # Strafe
        'left_y': -left_y,   # Forward (invert Y)
        'right_x': right_x,  # Rotate
        'right_y': -right_y, # Gimbal/arm (invert Y)
    }


def run_simulation(joystick, mode):
    """Run simulation mode - display robot and respond to joystick."""
    
    # Load robot image
    cli_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(cli_dir)
    img_path = os.path.join(project_dir, 'basic_simu', 'img', 'Robo-Top-mini.png')
    
    if not os.path.exists(img_path):
        click.echo(f"❌ Robot image not found at {img_path}")
        return
    
    robot_img = pygame.image.load(img_path)
    robot_img = pygame.transform.scale(robot_img, (60, 60))  # Scale to reasonable size
    
    # Window setup
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("RoboMaster Drive Simulation")
    
    # Robot state
    robot_x = WINDOW_WIDTH // 2
    robot_y = WINDOW_HEIGHT // 2
    robot_angle = 0  # Degrees
    
    # Trail for visualization
    trail = []
    MAX_TRAIL = 500
    
    # Speed factors for simulation
    MOVE_SPEED = 100  # pixels per second
    ROTATE_SPEED = 90  # degrees per second
    
    clock = pygame.time.Clock()
    FPS = 60
    
    click.echo(f"\n🎮 Simulation mode active!")
    click.echo("   Left stick: Move robot")
    click.echo("   Right stick X: Rotate robot")
    click.echo("   Press q/ESC or close window to quit\n")
    
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  # Delta time in seconds
        
        # Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    running = False
        
        # Get joystick state
        state = get_joystick_state(joystick)
        
        # Calculate movement based on robot's orientation
        angle_rad = math.radians(robot_angle)
        
        # Forward/backward (left_y) and strafe (left_x)
        forward = state['left_y'] * MOVE_SPEED * dt
        strafe = state['left_x'] * MOVE_SPEED * dt
        
        # Calculate dx, dy considering robot orientation
        dx = forward * math.cos(angle_rad) - strafe * math.sin(angle_rad)
        dy = -forward * math.sin(angle_rad) - strafe * math.cos(angle_rad)
        
        # Rotation (right_x)
        rotation = state['right_x'] * ROTATE_SPEED * dt
        
        # Update robot state
        robot_x += dx
        robot_y += dy
        robot_angle += rotation
        
        # Keep angle in 0-360 range
        robot_angle = robot_angle % 360
        
        # Keep robot in bounds
        robot_x = max(30, min(WINDOW_WIDTH - 30, robot_x))
        robot_y = max(30, min(WINDOW_HEIGHT - 30, robot_y))
        
        # Add to trail
        if len(trail) >= MAX_TRAIL:
            trail.pop(0)
        trail.append((int(robot_x), int(robot_y)))
        
        # Draw
        screen.fill((40, 40, 40))  # Dark background
        
        # Draw grid
        for x in range(0, WINDOW_WIDTH, 50):
            pygame.draw.line(screen, (60, 60, 60), (x, 0), (x, WINDOW_HEIGHT))
        for y in range(0, WINDOW_HEIGHT, 50):
            pygame.draw.line(screen, (60, 60, 60), (0, y), (WINDOW_WIDTH, y))
        
        # Draw trail
        for i, (tx, ty) in enumerate(trail):
            alpha = int(100 + 155 * i / len(trail)) if trail else 255
            pygame.draw.circle(screen, (alpha, alpha, alpha), (tx, ty), 2)
        
        # Draw robot
        rotated_img = pygame.transform.rotate(robot_img, robot_angle)
        rect = rotated_img.get_rect(center=(int(robot_x), int(robot_y)))
        screen.blit(rotated_img, rect.topleft)
        
        # Draw info overlay
        font = pygame.font.Font(None, 24)
        
        # Joystick values
        texts = [
            f"Left stick:  ({state['left_x']:+.2f}, {state['left_y']:+.2f})",
            f"Right stick: ({state['right_x']:+.2f}, {state['right_y']:+.2f})",
            f"Position: ({robot_x:.1f}, {robot_y:.1f})",
            f"Angle: {robot_angle:.1f}°",
            f"Mode: {mode} (simulation)",
        ]
        
        y_offset = 10
        for text in texts:
            text_surface = font.render(text, True, (0, 255, 0))
            screen.blit(text_surface, (10, y_offset))
            y_offset += 25
        
        # Help text at bottom
        help_text = "q/ESC to quit | Left stick: move | Right stick X: rotate"
        help_surface = font.render(help_text, True, (150, 150, 150))
        screen.blit(help_surface, (10, WINDOW_HEIGHT - 30))
        
        pygame.display.flip()
    
    click.echo("🛑 Simulation ended")


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
    
    Left stick: Move forward/backward and strafe left/right
    Right stick: Rotate left/right and control gimbal/arm up/down
    
    Use --simu for simulation mode without robot connection.
    
    Press 'q' or ESC to quit.
    """
    
    # Initialize joystick
    click.echo("🎮 Initializing joystick...")
    try:
        joystick = init_joystick()
        click.echo(f"✓ Joystick detected: {joystick.get_name()}")
        click.echo(f"  Axes: {joystick.get_numaxes()}, Buttons: {joystick.get_numbuttons()}")
    except RuntimeError as e:
        click.echo(f"❌ {e}")
        return
    
    # Simulation mode
    if simu:
        run_simulation(joystick, mode)
        pygame.quit()
        return
    
    # Real robot mode - import here to avoid errors in simu mode
    from robomaster import camera
    from .connection import connect_robot
    
    # Resolution map
    res_map = {
        '360p': camera.STREAM_360P,
        '540p': camera.STREAM_540P,
        '720p': camera.STREAM_720P,
    }
    
    with connect_robot(local_ip, robot_ip) as ep_robot:
        chassis = ep_robot.chassis
        
        # Try to get gimbal/arm
        gimbal = None
        arm = None
        try:
            gimbal = ep_robot.gimbal
            click.echo("✓ Gimbal detected")
        except:
            pass
        
        try:
            arm = ep_robot.robotic_arm
            click.echo("✓ Robotic arm detected")
        except:
            pass
        
        # Start video if enabled
        ep_camera = None
        if not no_video:
            try:
                ep_camera = ep_robot.camera
                ep_camera.start_video_stream(display=False, resolution=res_map.get(resolution))
                click.echo(f"📹 Video stream started ({resolution})")
            except Exception as e:
                click.echo(f"⚠️  Video failed: {e}")
                no_video = True
        
        click.echo(f"\n🚗 Ready to drive! Mode: {mode}")
        click.echo("   Left stick: Move | Right stick: Rotate/Gimbal")
        click.echo("   Press 'q' or ESC to quit\n")
        
        last_move_time = 0
        move_interval = MOVEMENT['move_interval']
        
        try:
            while True:
                # Read joystick
                state = get_joystick_state(joystick)
                
                current_time = time.time()
                
                # Movement control
                if mode == 'continuous':
                    # Continuous mode - send speed directly
                    vx = state['left_y'] * MOVEMENT['continuous_speed_xy']
                    vy = state['left_x'] * MOVEMENT['continuous_speed_xy']
                    vz = state['right_x'] * MOVEMENT['continuous_speed_z']
                    
                    if abs(vx) > 0.01 or abs(vy) > 0.01 or abs(vz) > 0.01:
                        chassis.drive_speed(x=vx, y=vy, z=vz, timeout=0.5)
                
                elif mode == 'step':
                    # Step mode - discrete movements with interval
                    if current_time - last_move_time >= move_interval:
                        if abs(state['left_y']) > 0.5 or abs(state['left_x']) > 0.5 or abs(state['right_x']) > 0.5:
                            x = MOVEMENT['step_forward'] if state['left_y'] > 0.5 else (-MOVEMENT['step_forward'] if state['left_y'] < -0.5 else 0)
                            y = MOVEMENT['step_strafe'] if state['left_x'] > 0.5 else (-MOVEMENT['step_strafe'] if state['left_x'] < -0.5 else 0)
                            z = MOVEMENT['step_rotate'] if state['right_x'] > 0.5 else (-MOVEMENT['step_rotate'] if state['right_x'] < -0.5 else 0)
                            
                            if x != 0 or y != 0 or z != 0:
                                chassis.move(x=x, y=y, z=z, 
                                            xy_speed=MOVEMENT['speed_xy'], 
                                            z_speed=MOVEMENT['speed_z'])
                                last_move_time = current_time
                
                # Gimbal/Arm control with right stick Y
                if state['right_y'] != 0:
                    if gimbal:
                        try:
                            pitch_delta = state['right_y'] * GIMBAL['step_pitch']
                            gimbal.move(pitch=pitch_delta, yaw=0, pitch_speed=GIMBAL['speed'], yaw_speed=GIMBAL['speed'])
                        except:
                            pass
                    elif arm:
                        try:
                            y_delta = state['right_y'] * ARM['step_y']
                            arm.move(x=0, y=y_delta)
                        except:
                            pass
                
                # Video display
                if ep_camera and not no_video:
                    img = ep_camera.read_cv2_image(strategy="newest", timeout=0.1)
                    if img is not None:
                        # Add overlay info
                        cv2.putText(img, f"L: ({state['left_x']:.1f}, {state['left_y']:.1f})", 
                                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        cv2.putText(img, f"R: ({state['right_x']:.1f}, {state['right_y']:.1f})", 
                                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        cv2.putText(img, f"Mode: {mode}", 
                                   (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        cv2.imshow("RoboMaster Drive", img)
                
                # Check for quit (video window or pygame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:
                    break
                
                # Also check pygame events for quit
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        break
                
                # Small delay
                time.sleep(0.02)
                
        except KeyboardInterrupt:
            pass
        
        finally:
            # Stop movement
            click.echo("\n🛑 Stopping robot...")
            try:
                chassis.drive_speed(x=0, y=0, z=0)
            except:
                pass
            
            # Cleanup video
            if ep_camera:
                try:
                    cv2.destroyAllWindows()
                    ep_camera.stop_video_stream()
                except:
                    pass
            
            # Cleanup pygame
            pygame.quit()


if __name__ == '__main__':
    drive()
