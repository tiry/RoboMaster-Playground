"""
RoboMaster CLI - Command line interface for controlling RoboMaster robots.

Usage:
    robomaster info      - Get robot information
    robomaster video     - Open video feed
    
Add new commands by creating a new module in the cli/ folder.
"""

import click
from .info import info
from .video import video


@click.group()
@click.version_option(version='0.1.0', prog_name='robomaster')
def cli():
    """RoboMaster Robot CLI - Control your robot from the command line."""
    pass


# Register commands from separate modules
cli.add_command(info)
cli.add_command(video)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()
