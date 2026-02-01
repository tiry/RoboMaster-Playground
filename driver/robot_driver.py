"""
Abstract robot driver interface.

Defines the high-level interface for controlling a RoboMaster robot.
Different implementations can use SDK, text protocol, or simulation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Callable, Any
import numpy as np
import threading


@dataclass
class RobotStatus:
    """Current robot status."""
    connected: bool = False
    arm_ready: bool = True
    arm_status: str = "Unknown"
    gripper_open: bool = True
    battery: Optional[int] = None


class ActionController:
    """Base controller for actions that need completion tracking.
    
    This class manages action execution with non-blocking command execution
    and threaded waiting for completion.
    """
    
    def __init__(self, name: str = "Action"):
        self._is_moving = False
        self._lock = threading.Lock()
        self._last_status = "Ready"
        self._name = name
    
    def is_ready(self) -> bool:
        """Check if ready for new command."""
        with self._lock:
            return not self._is_moving
    
    def get_status(self) -> str:
        """Get current status string."""
        with self._lock:
            return self._last_status
    
    def _set_status(self, status: str, is_moving: bool = None):
        """Update status thread-safely."""
        with self._lock:
            self._last_status = status
            if is_moving is not None:
                self._is_moving = is_moving
    
    def _wait_for_action(self, action, timeout: float = 5.0):
        """Background thread to wait for action completion."""
        try:
            self._set_status("Moving...", is_moving=True)
            
            if hasattr(action, 'wait_for_completed'):
                result = action.wait_for_completed(timeout=timeout)
                self._set_status("Completed" if result else "Timeout", is_moving=False)
            else:
                self._set_status("Completed", is_moving=False)
                
        except Exception as e:
            self._set_status(f"Error: {e}", is_moving=False)
    
    def execute_action(self, action) -> bool:
        """Execute action with background completion waiting.
        
        Args:
            action: Action object with wait_for_completed() method
            
        Returns:
            bool: True if command was started
        """
        if not self.is_ready():
            return False
        
        t = threading.Thread(target=self._wait_for_action, args=(action,), daemon=True)
        t.start()
        return True


class ArmController(ActionController):
    """Arm controller with threaded action completion waiting."""
    
    def __init__(self):
        super().__init__(name="Arm")
    
    def execute_move(self, action) -> bool:
        """Execute arm move (alias for execute_action)."""
        return self.execute_action(action)


class ChassisController(ActionController):
    """Chassis controller for step moves with action tracking."""
    
    def __init__(self):
        super().__init__(name="Chassis")


class RobotDriver(ABC):
    """Abstract base class for robot control.
    
    Implementations can use different protocols:
    - SDKDriver: Uses RoboMaster SDK
    - TextDriver: Uses text-based protocol
    - SimulationDriver: For testing without hardware
    """
    
    @abstractmethod
    def connect(self, local_ip: Optional[str] = None, robot_ip: Optional[str] = None) -> bool:
        """Connect to the robot.
        
        Args:
            local_ip: Local IP address (optional)
            robot_ip: Robot IP address (optional)
        
        Returns:
            bool: True if connected successfully
        """
        pass
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from the robot."""
        pass
    
    @abstractmethod
    def get_status(self) -> RobotStatus:
        """Get current robot status.
        
        Returns:
            RobotStatus: Current status
        """
        pass
    
    # --- Chassis control ---
    
    @abstractmethod
    def drive_speed(self, vx: float, vy: float, vz: float, timeout: float = 0.5):
        """Set chassis speed (continuous mode).
        
        Args:
            vx: Forward/backward speed (m/s)
            vy: Left/right strafe speed (m/s)
            vz: Rotation speed (deg/s)
            timeout: Command timeout
        """
        pass
    
    @abstractmethod
    def drive_move(self, x: float, y: float, z: float, 
                   xy_speed: float = 0.5, z_speed: float = 60):
        """Move chassis by distance (step mode).
        
        Args:
            x: Forward/backward distance (m)
            y: Left/right distance (m)
            z: Rotation angle (deg)
            xy_speed: Linear speed (m/s)
            z_speed: Rotation speed (deg/s)
        """
        pass
    
    @abstractmethod
    def stop(self):
        """Stop all movement immediately."""
        pass
    
    @abstractmethod
    def is_chassis_ready(self) -> bool:
        """Check if chassis is ready for new step move command.
        
        Returns:
            bool: True if chassis is ready (no move in progress)
        """
        pass
    
    # --- Arm control ---
    
    @abstractmethod
    def arm_move(self, x: float, y: float) -> bool:
        """Move robotic arm.
        
        Args:
            x: Horizontal movement (mm)
            y: Vertical movement (mm)
        
        Returns:
            bool: True if command was sent
        """
        pass
    
    @abstractmethod
    def is_arm_ready(self) -> bool:
        """Check if arm is ready for new command.
        
        Returns:
            bool: True if arm is ready
        """
        pass
    
    # --- Gripper control ---
    
    @abstractmethod
    def gripper_open(self, power: int = 50):
        """Open the gripper.
        
        Args:
            power: Gripper power (1-100)
        """
        pass
    
    @abstractmethod
    def gripper_close(self, power: int = 50):
        """Close the gripper.
        
        Args:
            power: Gripper power (1-100)
        """
        pass
    
    @abstractmethod
    def gripper_stop(self):
        """Stop gripper movement."""
        pass
    
    # --- Video ---
    
    @abstractmethod
    def start_video(self, resolution: str = '360p') -> bool:
        """Start video stream.
        
        Args:
            resolution: Video resolution ('360p', '540p', '720p')
        
        Returns:
            bool: True if started successfully
        """
        pass
    
    @abstractmethod
    def stop_video(self):
        """Stop video stream."""
        pass
    
    @abstractmethod
    def get_video_frame(self) -> Optional[np.ndarray]:
        """Get current video frame.
        
        Returns:
            np.ndarray: BGR image, or None if not available
        """
        pass
    
    # --- Context manager support ---
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
