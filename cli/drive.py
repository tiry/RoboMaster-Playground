"""
CLI command: Drive the robot with a USB joystick while viewing video feed.

Designed for EP Engineering Robot (arm + gripper).

Left stick: Forward/backward and strafe left/right
Right stick X: Rotate left/right
Right stick Y: Arm camera up/down

Includes simulation mode (--simu) to test controls without robot connection.
"""

import click
import cv2
import pygame
import time
import math
import os
import threading
from .config import (
    JOYSTICK_AXES, JOYSTICK_BUTTONS, DEADZONE,
    MOVEMENT, ARM, STICK_OVERLAY_MODE, apply_deadzone
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
    
    # Triggers (0 to 1) - for arm X axis
    # Note: Xbox triggers start at -1 (released) and go to 1 (pressed)
    left_trigger = (joystick.get_axis(JOYSTICK_AXES['left_trigger']) + 1) / 2  # Normalize to 0-1
    right_trigger = (joystick.get_axis(JOYSTICK_AXES['right_trigger']) + 1) / 2  # Normalize to 0-1
    
    # Bumpers (buttons)
    lb_pressed = joystick.get_button(JOYSTICK_BUTTONS['lb'])
    rb_pressed = joystick.get_button(JOYSTICK_BUTTONS['rb'])
    
    # A button for speed boost
    a_pressed = joystick.get_button(JOYSTICK_BUTTONS['a'])
    
    return {
        'left_x': left_x,              # Strafe
        'left_y': -left_y,             # Forward (invert Y)
        'right_x': right_x,            # Rotate
        'right_y': -right_y,           # Arm Y (invert Y)
        'left_trigger': left_trigger,   # Arm retract
        'right_trigger': right_trigger, # Arm extend
        'lb': lb_pressed,               # Gripper close
        'rb': rb_pressed,               # Gripper open
        'a': a_pressed,                 # Speed boost
    }


class ArmController:
    """Arm controller with threaded action completion waiting.
    
    Uses a background thread to wait for action completion, 
    so the main loop isn't blocked.
    """
    
    def __init__(self, arm):
        self.arm = arm
        self._is_moving = False
        self._lock = threading.Lock()
        self._last_status = "Ready"
    
    def is_ready(self):
        """Check if arm is ready for a new command."""
        with self._lock:
            return not self._is_moving
    
    def get_status(self):
        """Get current action status for display."""
        with self._lock:
            return self._last_status
    
    def _wait_for_action(self, action):
        """Background thread to wait for action completion."""
        try:
            with self._lock:
                self._is_moving = True
                self._last_status = "Moving..."
            
            # Wait for the action to complete (blocking)
            result = action.wait_for_completed(timeout=5.0)
            
            with self._lock:
                if result:
                    self._last_status = "Completed"
                else:
                    self._last_status = "Timeout"
                self._is_moving = False
        except Exception as e:
            with self._lock:
                self._last_status = f"Error: {e}"
                self._is_moving = False
    
    def move(self, x=0, y=0):
        """Send arm move command (non-blocking)."""
        if not self.is_ready():
            return False
        
        try:
            action = self.arm.move(x=x, y=y)
            # Start background thread to wait for completion
            t = threading.Thread(target=self._wait_for_action, args=(action,), daemon=True)
            t.start()
            return True
        except Exception as e:
            with self._lock:
                self._last_status = f"Send error: {e}"
            return False


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
    robot_img = pygame.transform.scale(robot_img, (60, 60))
    
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("RoboMaster Drive Simulation")
    
    robot_x = WINDOW_WIDTH // 2
    robot_y = WINDOW_HEIGHT // 2
    robot_angle = 0
    arm_y = 0  # Simulated arm Y position
    
    trail = []
    MAX_TRAIL = 500
    
    MOVE_SPEED = 100
    ROTATE_SPEED = 90
    
    clock = pygame.time.Clock()
    FPS = 60
    
    click.echo(f"\n🎮 Simulation mode active!")
    click.echo("   Left stick: Move robot")
    click.echo("   Right stick X: Rotate robot")
    click.echo("   Right stick Y: Arm up/down")
    click.echo("   Press q/ESC to quit\n")
    
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    running = False
        
        state = get_joystick_state(joystick)
        angle_rad = math.radians(robot_angle)
        
        forward = state['left_y'] * MOVE_SPEED * dt
        strafe = state['left_x'] * MOVE_SPEED * dt
        
        dx = forward * math.cos(angle_rad) - strafe * math.sin(angle_rad)
        dy = -forward * math.sin(angle_rad) - strafe * math.cos(angle_rad)
        rotation = state['right_x'] * ROTATE_SPEED * dt
        
        # Arm simulation
        arm_y += state['right_y'] * ARM['step_y'] * 5 * dt
        arm_y = max(0, min(100, arm_y))  # Clamp to 0-100mm range
        
        robot_x += dx
        robot_y += dy
        robot_angle = robot_angle % 360
        robot_angle += rotation
        
        robot_x = max(30, min(WINDOW_WIDTH - 30, robot_x))
        robot_y = max(30, min(WINDOW_HEIGHT - 30, robot_y))
        
        if len(trail) >= MAX_TRAIL:
            trail.pop(0)
        trail.append((int(robot_x), int(robot_y)))
        
        screen.fill((40, 40, 40))
        
        for x in range(0, WINDOW_WIDTH, 50):
            pygame.draw.line(screen, (60, 60, 60), (x, 0), (x, WINDOW_HEIGHT))
        for y in range(0, WINDOW_HEIGHT, 50):
            pygame.draw.line(screen, (60, 60, 60), (0, y), (WINDOW_WIDTH, y))
        
        for i, (tx, ty) in enumerate(trail):
            alpha = int(100 + 155 * i / len(trail)) if trail else 255
            pygame.draw.circle(screen, (alpha, alpha, alpha), (tx, ty), 2)
        
        rotated_img = pygame.transform.rotate(robot_img, robot_angle)
        rect = rotated_img.get_rect(center=(int(robot_x), int(robot_y)))
        screen.blit(rotated_img, rect.topleft)
        
        font = pygame.font.Font(None, 24)
        texts = [
            f"Left stick:  ({state['left_x']:+.2f}, {state['left_y']:+.2f})",
            f"Right stick: ({state['right_x']:+.2f}, {state['right_y']:+.2f})",
            f"Position: ({robot_x:.1f}, {robot_y:.1f})",
            f"Angle: {robot_angle:.1f}°",
            f"Arm Y: {arm_y:.1f}mm",
            f"Mode: {mode} (simulation)",
        ]
        
        y_offset = 10
        for text in texts:
            text_surface = font.render(text, True, (0, 255, 0))
            screen.blit(text_surface, (10, y_offset))
            y_offset += 25
        
        help_text = "q/ESC to quit | Left: move | Right X: rotate | Right Y: arm"
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
    
    Designed for EP Engineering Robot.
    
    Left stick: Move forward/backward and strafe left/right
    Right stick X: Rotate left/right
    Right stick Y: Arm camera up/down
    
    Use --simu for simulation mode without robot connection.
    
    Press 'q' or ESC to quit.
    """
    
    click.echo("🎮 Initializing joystick...")
    try:
        joystick = init_joystick()
        click.echo(f"✓ Joystick detected: {joystick.get_name()}")
        click.echo(f"  Axes: {joystick.get_numaxes()}, Buttons: {joystick.get_numbuttons()}")
    except RuntimeError as e:
        click.echo(f"❌ {e}")
        return
    
    if simu:
        run_simulation(joystick, mode)
        pygame.quit()
        return
    
    from robomaster import camera
    from .connection import connect_robot
    
    res_map = {
        '360p': camera.STREAM_360P,
        '540p': camera.STREAM_540P,
        '720p': camera.STREAM_720P,
    }
    
    with connect_robot(local_ip, robot_ip) as ep_robot:
        chassis = ep_robot.chassis
        
        # Set SDK stick overlay mode
        try:
            chassis.stick_overlay(fusion_mode=STICK_OVERLAY_MODE)
            overlay_names = {0: "SDK only", 1: "Overlay (body)", 2: "Overlay (gimbal)"}
            click.echo(f"✓ Chassis mode: {overlay_names.get(STICK_OVERLAY_MODE, STICK_OVERLAY_MODE)}")
        except Exception as e:
            click.echo(f"⚠️  Could not set stick_overlay: {e}")
        
        # Get arm (EP Engineering robot)
        arm_controller = None
        try:
            arm = ep_robot.robotic_arm
            arm_controller = ArmController(arm)
            click.echo("✓ Robotic arm detected")
        except:
            click.echo("⚠️  No robotic arm detected")
        
        # Get gripper
        gripper = None
        try:
            gripper = ep_robot.gripper
            click.echo("✓ Gripper detected")
        except:
            click.echo("⚠️  No gripper detected")
        
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
        click.echo("   Left stick: Move | Right stick X: Rotate")
        click.echo("   Right stick Y: Arm up/down | Triggers: Arm extend/retract")
        click.echo("   LB: Close gripper | RB: Open gripper | A: Speed boost")
        click.echo("   Press 'q' or ESC to quit\n")
        
        last_move_time = 0
        move_interval = MOVEMENT['move_interval']
        
        try:
            while True:
                state = get_joystick_state(joystick)
                current_time = time.time()
                
                # Speed multiplier (A button for boost)
                speed_mult = MOVEMENT.get('boost_multiplier', 2.0) if state['a'] else 1.0
                
                # Chassis control
                try:
                    if mode == 'continuous':
                        vx = state['left_y'] * MOVEMENT['continuous_speed_xy'] * speed_mult
                        vy = state['left_x'] * MOVEMENT['continuous_speed_xy'] * speed_mult
                        vz = state['right_x'] * MOVEMENT['continuous_speed_z'] * speed_mult
                        
                        if abs(vx) > 0.01 or abs(vy) > 0.01 or abs(vz) > 0.01:
                            chassis.drive_speed(x=vx, y=vy, z=vz, timeout=0.5)
                    
                    elif mode == 'step':
                        if current_time - last_move_time >= move_interval:
                            if abs(state['left_y']) > 0.5 or abs(state['left_x']) > 0.5 or abs(state['right_x']) > 0.5:
                                x = MOVEMENT['step_forward'] if state['left_y'] > 0.5 else (-MOVEMENT['step_forward'] if state['left_y'] < -0.5 else 0)
                                y = MOVEMENT['step_strafe'] if state['left_x'] > 0.5 else (-MOVEMENT['step_strafe'] if state['left_x'] < -0.5 else 0)
                                z = MOVEMENT['step_rotate'] if state['right_x'] > 0.5 else (-MOVEMENT['step_rotate'] if state['right_x'] < -0.5 else 0)
                                
                                if x != 0 or y != 0 or z != 0:
                                    try:
                                        chassis.move(x=x, y=y, z=z, 
                                                    xy_speed=MOVEMENT['speed_xy'], 
                                                    z_speed=MOVEMENT['speed_z'])
                                    except:
                                        pass
                                    last_move_time = current_time
                except Exception:
                    pass
                
                # Arm control - only send when ready (previous action complete)
                if arm_controller and arm_controller.is_ready():
                    # Right stick Y for arm up/down
                    y_delta = 0
                    if abs(state['right_y']) > 0.3:
                        y_delta = int(state['right_y'] * ARM['step_y'])
                    
                    # Triggers for arm extend/retract
                    x_delta = 0
                    if state['right_trigger'] > 0.3:  # Extend
                        x_delta = int(state['right_trigger'] * ARM['step_x'])
                    elif state['left_trigger'] > 0.3:  # Retract
                        x_delta = -int(state['left_trigger'] * ARM['step_x'])
                    
                    if x_delta != 0 or y_delta != 0:
                        arm_controller.move(x=x_delta, y=y_delta)
                
                # Gripper control (bumpers)
                if gripper:
                    if state['lb']:  # Left bumper = close
                        try:
                            gripper.close(power=50)
                        except:
                            pass
                    elif state['rb']:  # Right bumper = open
                        try:
                            gripper.open(power=50)
                        except:
                            pass
                
                # Video display
                if ep_camera and not no_video:
                    img = ep_camera.read_cv2_image(strategy="newest", timeout=0.1)
                    if img is not None:
                        cv2.putText(img, f"L: ({state['left_x']:.1f}, {state['left_y']:.1f})", 
                                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        cv2.putText(img, f"R: ({state['right_x']:.1f}, {state['right_y']:.1f})", 
                                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        speed_text = f"Mode: {mode}" + (" [BOOST]" if state['a'] else "")
                        color = (0, 255, 255) if state['a'] else (0, 255, 0)  # Yellow when boosting
                        cv2.putText(img, speed_text, 
                                   (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                        
                        # Show arm and gripper status
                        if arm_controller:
                            arm_status = arm_controller.get_status()
                            cv2.putText(img, f"Arm: {arm_status}", 
                                       (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        
                        # Show trigger/gripper info
                        cv2.putText(img, f"Triggers: L={state['left_trigger']:.1f} R={state['right_trigger']:.1f}", 
                                   (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        gripper_text = "CLOSE" if state['lb'] else ("OPEN" if state['rb'] else "-")
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
            
            for _ in range(3):
                try:
                    chassis.drive_speed(x=0, y=0, z=0)
                    break
                except:
                    pass
            
            # Stop gripper
            if gripper:
                try:
                    gripper.pause()
                except:
                    pass
            
            if ep_camera:
                try:
                    cv2.destroyAllWindows()
                except:
                    pass
                try:
                    ep_camera.stop_video_stream()
                except:
                    pass
            
            try:
                pygame.quit()
            except:
                pass
            
            click.echo("✓ Robot stopped")


if __name__ == '__main__':
    drive()
