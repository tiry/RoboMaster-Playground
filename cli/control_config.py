"""
CLI command: Controller configuration helper.

Shows real-time joystick input to help identify axis and button mappings.
"""

import click
import pygame
import time


@click.command()
def control_config():
    """
    Interactive controller configuration helper.
    
    Shows real-time axis and button values to help configure your controller.
    Move sticks and press buttons to see their values.
    
    Press Ctrl+C or close window to exit.
    """
    
    click.echo("🎮 Controller Configuration Helper")
    click.echo("=" * 50)
    
    # Check for /dev/input/js* devices first
    import os
    import glob
    
    js_devices = glob.glob('/dev/input/js*')
    click.echo(f"\n🔍 System joystick devices: {js_devices if js_devices else 'None found'}")
    
    # Check USB devices
    try:
        import subprocess
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        controllers = [l for l in result.stdout.split('\n') 
                      if any(x in l.lower() for x in ['sony', 'dual', 'game', 'controller', 'xbox'])]
        if controllers:
            click.echo(f"🎮 USB controllers detected:")
            for c in controllers:
                click.echo(f"   {c}")
    except:
        pass
    
    # Set SDL environment for Linux
    os.environ.setdefault('SDL_JOYSTICK_DEVICE', '/dev/input/js0')
    
    # Initialize pygame with display (required for joystick on some systems)
    pygame.init()
    
    # Create window first - some systems need this
    screen = pygame.display.set_mode((500, 350))
    pygame.display.set_caption("Controller Config - Move sticks/press buttons")
    
    # Now init joystick
    pygame.joystick.init()
    
    # Give it a moment and pump events
    time.sleep(0.5)
    pygame.event.pump()
    
    # Check for controllers
    count = pygame.joystick.get_count()
    click.echo(f"\n📊 Pygame detected {count} joystick(s)")
    
    if count == 0:
        click.echo("\n❌ No joystick detected by pygame!")
        click.echo("\n📝 Troubleshooting tips:")
        click.echo("   1. Check if your user is in the 'input' group:")
        click.echo("      groups $USER")
        click.echo("   2. Add yourself to input group if needed:")
        click.echo("      sudo usermod -aG input $USER")
        click.echo("   3. Then logout and login again")
        click.echo("   4. Or run with sudo (not recommended)")
        click.echo("\n   Also try unplugging and replugging the controller.")
        pygame.quit()
        return
    
    # List all controllers
    click.echo(f"\n📋 Found {pygame.joystick.get_count()} controller(s):\n")
    for i in range(pygame.joystick.get_count()):
        js = pygame.joystick.Joystick(i)
        js.init()
        click.echo(f"  [{i}] {js.get_name()}")
        click.echo(f"      Axes: {js.get_numaxes()}, Buttons: {js.get_numbuttons()}, Hats: {js.get_numhats()}")
    
    # Use first controller
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    
    click.echo(f"\n✓ Using: {joystick.get_name()}")
    click.echo(f"  Axes: {joystick.get_numaxes()}")
    click.echo(f"  Buttons: {joystick.get_numbuttons()}")
    click.echo(f"  Hats (D-pad): {joystick.get_numhats()}")
    
    click.echo("\n" + "=" * 50)
    click.echo("Move sticks and press buttons to see values.")
    click.echo("Press Ctrl+C to exit.\n")
    
    # Create a small pygame window to receive events
    screen = pygame.display.set_mode((400, 300))
    pygame.display.set_caption("Controller Config - Close to exit")
    
    # Track significant changes
    prev_axes = [0.0] * joystick.get_numaxes()
    prev_buttons = [0] * joystick.get_numbuttons()
    
    try:
        running = True
        last_print = 0
        
        while running:
            # Process events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.JOYBUTTONDOWN:
                    click.echo(f"🔵 BUTTON {event.button} PRESSED")
                elif event.type == pygame.JOYBUTTONUP:
                    click.echo(f"⚪ Button {event.button} released")
                elif event.type == pygame.JOYHATMOTION:
                    click.echo(f"🎯 HAT {event.hat}: {event.value}")
            
            # Check axis changes
            changed = []
            for i in range(joystick.get_numaxes()):
                val = joystick.get_axis(i)
                if abs(val - prev_axes[i]) > 0.1:  # Significant change
                    prev_axes[i] = val
                    if abs(val) > 0.15:  # Above deadzone
                        changed.append(f"Axis {i}: {val:+.2f}")
            
            if changed:
                click.echo(f"📊 {', '.join(changed)}")
            
            # Periodic full status (every 2 seconds if idle)
            current_time = time.time()
            if current_time - last_print > 2:
                # Build axes summary
                axes_str = " ".join([f"{i}:{joystick.get_axis(i):+.1f}" for i in range(joystick.get_numaxes())])
                # Build buttons summary
                pressed = [str(i) for i in range(joystick.get_numbuttons()) if joystick.get_button(i)]
                buttons_str = f"Pressed: [{', '.join(pressed)}]" if pressed else "None pressed"
                
                # Update window
                screen.fill((30, 30, 30))
                font = pygame.font.Font(None, 24)
                
                y = 20
                text = font.render(f"Controller: {joystick.get_name()[:40]}", True, (255, 255, 255))
                screen.blit(text, (10, y)); y += 30
                
                text = font.render(f"Axes: {axes_str}", True, (100, 255, 100))
                screen.blit(text, (10, y)); y += 30
                
                text = font.render(f"Buttons: {buttons_str}", True, (100, 200, 255))
                screen.blit(text, (10, y)); y += 40
                
                # Show stick interpretation
                text = font.render("Typical PS5 mapping:", True, (200, 200, 200))
                screen.blit(text, (10, y)); y += 25
                text = font.render("  Left stick X/Y: Axes 0, 1", True, (150, 150, 150))
                screen.blit(text, (10, y)); y += 20
                text = font.render("  Right stick X/Y: Axes 2, 3", True, (150, 150, 150))
                screen.blit(text, (10, y)); y += 20
                text = font.render("  L2/R2 triggers: Axes 4, 5", True, (150, 150, 150))
                screen.blit(text, (10, y)); y += 30
                
                text = font.render("Close window or Ctrl+C to exit", True, (150, 150, 150))
                screen.blit(text, (10, y))
                
                pygame.display.flip()
                last_print = current_time
            
            time.sleep(0.02)
            
    except KeyboardInterrupt:
        pass
    
    finally:
        pygame.quit()
    
    # Print suggested config
    click.echo("\n" + "=" * 50)
    click.echo("\n📝 Suggested PS5 controller config for cli/config.py:\n")
    click.echo("""
JOYSTICK_AXES = {
    'left_x': 0,      # Left stick X
    'left_y': 1,      # Left stick Y  
    'right_x': 2,     # Right stick X (may be 3 on some systems)
    'right_y': 3,     # Right stick Y (may be 4 on some systems)
    'left_trigger': 4,
    'right_trigger': 5,
}

# PS5 DualSense button mapping (may vary)
JOYSTICK_BUTTONS = {
    'cross': 0,       # X button
    'circle': 1,      # O button
    'square': 2,      # □ button
    'triangle': 3,    # △ button
    'l1': 4,
    'r1': 5,
    'l2_button': 6,   # L2 click (not trigger)
    'r2_button': 7,   # R2 click (not trigger)
    'share': 8,
    'options': 9,
    'ps': 10,
    'l3': 11,         # Left stick click
    'r3': 12,         # Right stick click
    'touchpad': 13,
}
""")


if __name__ == '__main__':
    control_config()
