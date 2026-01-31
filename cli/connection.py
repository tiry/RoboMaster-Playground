"""
Shared robot connection management for CLI commands.
"""

from contextlib import contextmanager
from robomaster import robot, config


# Default IP addresses
DEFAULT_LOCAL_IP = "192.168.2.20"
DEFAULT_ROBOT_IP = "192.168.2.1"


def configure_ips(local_ip: str = None, robot_ip: str = None):
    """Configure SDK IP addresses."""
    config.LOCAL_IP_STR = local_ip or DEFAULT_LOCAL_IP
    config.ROBOT_IP_STR = robot_ip or DEFAULT_ROBOT_IP


@contextmanager
def connect_robot(local_ip: str = None, robot_ip: str = None, verbose: bool = True):
    """
    Context manager for robot connection.
    
    Usage:
        with connect_robot() as ep_robot:
            # Use ep_robot here
            pass
    """
    configure_ips(local_ip, robot_ip)
    
    if verbose:
        print(f"Connecting to robot...")
        print(f"  Local IP: {config.LOCAL_IP_STR}")
        print(f"  Robot IP: {config.ROBOT_IP_STR}")
    
    ep_robot = robot.Robot()
    
    try:
        ep_robot.initialize(conn_type="sta")
        if verbose:
            print("✓ Connected!")
        yield ep_robot
    finally:
        if verbose:
            print("Closing connection...")
        ep_robot.close()
        if verbose:
            print("✓ Disconnected.")
