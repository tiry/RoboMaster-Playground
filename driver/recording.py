"""
Recording driver wrapper.

Wraps any RobotDriver to record commands while delegating to the underlying driver.
"""

from typing import Optional
import numpy as np

from .robot_driver import RobotDriver, RobotStatus
from cli.recorder import CommandRecorder


class RecordingDriver(RobotDriver):
    """Wrapper that records commands while delegating to underlying driver."""
    
    def __init__(self, driver: RobotDriver, recorder: CommandRecorder):
        """Initialize recording driver.
        
        Args:
            driver: The underlying driver to delegate to
            recorder: CommandRecorder instance to record commands
        """
        self._driver = driver
        self._recorder = recorder
    
    # --- Pass-through methods ---
    
    def connect(self, local_ip: Optional[str] = None, robot_ip: Optional[str] = None, 
                **kwargs) -> bool:
        return self._driver.connect(local_ip, robot_ip, **kwargs)
    
    def disconnect(self):
        self._driver.disconnect()
    
    def get_status(self) -> RobotStatus:
        return self._driver.get_status()
    
    def is_chassis_ready(self) -> bool:
        return self._driver.is_chassis_ready()
    
    def is_arm_ready(self) -> bool:
        return self._driver.is_arm_ready()
    
    def start_video(self, resolution: str = '360p') -> bool:
        return self._driver.start_video(resolution)
    
    def stop_video(self):
        self._driver.stop_video()
    
    def get_video_frame(self) -> Optional[np.ndarray]:
        return self._driver.get_video_frame()
    
    # --- Properties ---
    
    @property
    def has_arm(self) -> bool:
        return getattr(self._driver, 'has_arm', False)
    
    @property
    def has_gripper(self) -> bool:
        return getattr(self._driver, 'has_gripper', False)
    
    @property
    def arm_status(self) -> str:
        return getattr(self._driver, 'arm_status', 'N/A')
    
    # --- Recorded methods ---
    
    def drive_speed(self, vx: float, vy: float, vz: float, timeout: float = 0.5):
        """Record and execute chassis speed command."""
        self._recorder.record_chassis_speed(vx, vy, vz)
        self._driver.drive_speed(vx, vy, vz, timeout)
    
    def drive_move(self, x: float, y: float, z: float, 
                   xy_speed: float = 0.5, z_speed: float = 60) -> bool:
        """Record and execute chassis move command."""
        self._recorder.record_chassis_move(x, y, z, xy_speed, z_speed)
        return self._driver.drive_move(x, y, z, xy_speed, z_speed)
    
    def stop(self):
        """Record and execute stop command."""
        self._recorder.record_stop()
        self._driver.stop()
    
    def arm_move(self, x: float, y: float) -> bool:
        """Record and execute arm move command."""
        self._recorder.record_arm_move(x, y)
        return self._driver.arm_move(x, y)
    
    def arm_recenter(self) -> bool:
        """Record and execute arm recenter command."""
        self._recorder.record_arm_recenter()
        return self._driver.arm_recenter()
    
    def gripper_open(self, power: int = 50):
        """Record and execute gripper open command."""
        self._recorder.record_gripper_open(power)
        self._driver.gripper_open(power)
    
    def gripper_close(self, power: int = 50):
        """Record and execute gripper close command."""
        self._recorder.record_gripper_close(power)
        self._driver.gripper_close(power)
    
    def gripper_stop(self):
        """Record and execute gripper stop command."""
        self._recorder.record_gripper_stop()
        self._driver.gripper_stop()
    
    def led_on(self, r: int = 255, g: int = 255, b: int = 255):
        """Execute LED on command (not recorded)."""
        self._driver.led_on(r, g, b)
    
    def led_off(self):
        """Execute LED off command (not recorded)."""
        self._driver.led_off()
    
    def led_toggle(self, r: int = 255, g: int = 255, b: int = 255) -> bool:
        """Execute LED toggle command (not recorded)."""
        return self._driver.led_toggle(r, g, b)
