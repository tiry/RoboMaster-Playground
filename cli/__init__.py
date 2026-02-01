"""
RoboMaster CLI - Command line interface for controlling RoboMaster robots.

Usage:
    robomaster info      - Get robot information
    robomaster video     - Open video feed
    robomaster drive     - Drive robot with USB joystick
    robomaster led       - Control robot LEDs
    
Add new commands by creating a new module in the cli/ folder.
"""

import click
from .info import info
from .video import video
from .drive import drive
from .control_config import control_config
from .led import led


@click.group()
@click.version_option(version='0.1.0', prog_name='robomaster')
def cli():
    """RoboMaster Robot CLI - Control your robot from the command line."""
    pass


# Register commands from separate modules
cli.add_command(info)
cli.add_command(video)
cli.add_command(drive)
cli.add_command(control_config)
cli.add_command(led)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()
