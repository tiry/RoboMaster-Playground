"""
Simulation mode for testing joystick controls without a physical robot.

Displays a pygame window with a robot sprite that responds to joystick input.
"""

import click
import pygame
import math
import os

from cli.joystick import Joystick
from cli.config import ARM


def run_simulation(joystick: Joystick, mode: str):
    """Run simulation mode - display robot and respond to joystick.
    
    Args:
        joystick: Initialized Joystick instance
        mode: Drive mode ('continuous' or 'step')
    """
    
    # Load robot image
    cli_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(cli_dir)
    img_path = os.path.join(project_dir, 'basic_simu', 'img', 'Robo-Top-mini.png')
    
    if not os.path.exists(img_path):
        click.echo(f"❌ Robot image not found at {img_path}")
        return
    
    robot_img = pygame.image.load(img_path)
    robot_img = pygame.transform.scale(robot_img, (60, 60))
    
    # Window setup
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("RoboMaster Drive Simulation")
    
    # Robot state
    robot_x = WINDOW_WIDTH // 2
    robot_y = WINDOW_HEIGHT // 2
    robot_angle = 0
    arm_x = 50  # Simulated arm X position (mm)
    arm_y = 50  # Simulated arm Y position (mm)
    gripper_open = True
    
    # Trail for visualization
    trail = []
    MAX_TRAIL = 500
    
    # Speed settings
    MOVE_SPEED = 100
    ROTATE_SPEED = 90
    
    clock = pygame.time.Clock()
    FPS = 60
    
    click.echo(f"\n🎮 Simulation mode active!")
    click.echo("   Left stick: Move robot")
    click.echo("   Right stick X: Rotate robot")
    click.echo("   Right stick Y: Arm up/down")
    click.echo("   Triggers: Arm extend/retract")
    click.echo("   Bumpers: Gripper open/close")
    click.echo("   A button: Speed boost")
    click.echo("   Press q/ESC to quit\n")
    
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        
        # Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    running = False
        
        # Get joystick state
        state = joystick.get_state()
        
        # Speed boost
        speed_mult = 2.0 if state.a else 1.0
        
        # Calculate movement
        angle_rad = math.radians(robot_angle)
        forward = state.left_y * MOVE_SPEED * speed_mult * dt
        strafe = state.left_x * MOVE_SPEED * speed_mult * dt
        
        dx = forward * math.cos(angle_rad) - strafe * math.sin(angle_rad)
        dy = -forward * math.sin(angle_rad) - strafe * math.cos(angle_rad)
        rotation = state.right_x * ROTATE_SPEED * speed_mult * dt
        
        # Arm simulation
        arm_y += state.right_y * ARM['step_y'] * 5 * dt
        arm_y = max(0, min(100, arm_y))  # Clamp to 0-100mm range
        
        # Arm X (triggers)
        if state.right_trigger > 0.3:
            arm_x += state.right_trigger * ARM['step_x'] * 5 * dt
        elif state.left_trigger > 0.3:
            arm_x -= state.left_trigger * ARM['step_x'] * 5 * dt
        arm_x = max(0, min(200, arm_x))  # Clamp to 0-200mm range
        
        # Gripper simulation
        if state.lb:
            gripper_open = False
        elif state.rb:
            gripper_open = True
        
        # Update robot position
        robot_x += dx
        robot_y += dy
        robot_angle = robot_angle % 360
        robot_angle += rotation
        
        # Keep robot in bounds
        robot_x = max(30, min(WINDOW_WIDTH - 30, robot_x))
        robot_y = max(30, min(WINDOW_HEIGHT - 30, robot_y))
        
        # Update trail
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
        
        texts = [
            f"Left stick:  ({state.left_x:+.2f}, {state.left_y:+.2f})",
            f"Right stick: ({state.right_x:+.2f}, {state.right_y:+.2f})",
            f"Triggers: L={state.left_trigger:.1f} R={state.right_trigger:.1f}",
            f"Position: ({robot_x:.1f}, {robot_y:.1f})",
            f"Angle: {robot_angle:.1f}°",
            f"Arm: X={arm_x:.1f}mm Y={arm_y:.1f}mm",
            f"Gripper: {'OPEN' if gripper_open else 'CLOSED'}",
            f"Mode: {mode}" + (" [BOOST]" if state.a else ""),
        ]
        
        y_offset = 10
        for text in texts:
            color = (0, 255, 255) if state.a and "BOOST" in text else (0, 255, 0)
            text_surface = font.render(text, True, color)
            screen.blit(text_surface, (10, y_offset))
            y_offset += 25
        
        # Help text at bottom
        help_text = "q/ESC to quit | A: boost | LB/RB: gripper | Triggers: arm X"
        help_surface = font.render(help_text, True, (150, 150, 150))
        screen.blit(help_surface, (10, WINDOW_HEIGHT - 30))
        
        pygame.display.flip()
    
    click.echo("🛑 Simulation ended")
