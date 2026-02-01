"""
CLI command: Control robot LEDs.
"""

import click
from .connection import connect_robot


def parse_color(color: str) -> tuple:
    """Parse color string to RGB tuple.
    
    Supports formats:
    - Hex: #FF0000, FF0000
    - Names: red, green, blue, white, yellow, cyan, magenta, orange
    - RGB: 255,0,0 or 255 0 0
    """
    color = color.strip().lower()
    
    # Named colors
    colors = {
        'red': (255, 0, 0),
        'green': (0, 255, 0),
        'blue': (0, 0, 255),
        'white': (255, 255, 255),
        'yellow': (255, 255, 0),
        'cyan': (0, 255, 255),
        'magenta': (255, 0, 255),
        'orange': (255, 128, 0),
        'purple': (128, 0, 255),
        'pink': (255, 128, 128),
        'off': (0, 0, 0),
    }
    
    if color in colors:
        return colors[color]
    
    # Hex format
    if color.startswith('#'):
        color = color[1:]
    
    if len(color) == 6:
        try:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            return (r, g, b)
        except ValueError:
            pass
    
    # RGB format: 255,0,0 or 255 0 0
    parts = color.replace(',', ' ').split()
    if len(parts) == 3:
        try:
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            pass
    
    raise ValueError(f"Invalid color format: {color}")


@click.command()
@click.argument('action', type=click.Choice(['on', 'off', 'set']), default='on')
@click.option('--color', '-c', default='white', 
              help='LED color (name, hex, or RGB). Examples: red, #FF0000, 255,0,0')
@click.option('--local-ip', '-l', default=None, help='Local IP address')
@click.option('--robot-ip', '-r', default=None, help='Robot IP address')
def led(action, color, local_ip, robot_ip):
    """
    Control robot LEDs.
    
    \b
    Actions:
      on   - Turn LEDs on (default color: white)
      off  - Turn LEDs off
      set  - Set LED color
    
    \b
    Color formats:
      Named: red, green, blue, white, yellow, cyan, magenta, orange
      Hex:   #FF0000 or FF0000
      RGB:   255,0,0 or "255 0 0"
    
    \b
    Examples:
      robomaster led on              # White LEDs
      robomaster led on -c red       # Red LEDs
      robomaster led set -c #00FF00  # Green LEDs (hex)
      robomaster led off             # Turn off
    """
    
    # Parse color
    try:
        r, g, b = parse_color(color)
    except ValueError as e:
        click.echo(f"❌ {e}")
        return
    
    with connect_robot(local_ip, robot_ip) as robot:
        led_module = robot.led
        
        if action == 'off':
            click.echo("💡 Turning LEDs off...")
            led_module.set_led(comp="all", r=0, g=0, b=0, effect="off")
            click.echo("✓ LEDs off")
        
        elif action in ('on', 'set'):
            click.echo(f"💡 Setting LEDs to RGB({r}, {g}, {b})...")
            led_module.set_led(comp="all", r=r, g=g, b=b, effect="on")
            click.echo(f"✓ LEDs on ({color})")


if __name__ == '__main__':
    led()
