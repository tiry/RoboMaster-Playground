"""
SDK-based robot driver implementation.

Uses the RoboMaster SDK to control the robot.
"""

from typing import Optional
import numpy as np

from .robot_driver import RobotDriver, RobotStatus, ArmController, ChassisController
from cli.config import STICK_OVERLAY_MODE
from cli.connection import configure_ips


class SDKChassisController(ChassisController):
    """SDK-specific chassis controller for step moves."""
    
    def __init__(self, chassis):
        super().__init__()
        self._chassis = chassis
    
    def move(self, x: float, y: float, z: float, xy_speed: float, z_speed: float) -> bool:
        """Send chassis move command via SDK."""
        if not self.is_ready():
            return False
        
        try:
            action = self._chassis.move(x=x, y=y, z=z, xy_speed=xy_speed, z_speed=z_speed)
            return self.execute_action(action)
        except Exception as e:
            self._set_status(f"Send error: {e}", is_moving=False)
            return False


class SDKArmController(ArmController):
    """SDK-specific arm controller."""
    
    def __init__(self, arm):
        super().__init__()
        self._arm = arm
    
    def move(self, x: float, y: float) -> bool:
        """Send arm move command via SDK."""
        if not self.is_ready():
            return False
        
        try:
            action = self._arm.move(x=x, y=y)
            return self.execute_move(action)
        except Exception as e:
            self._set_status(f"Send error: {e}", is_moving=False)
            return False


class SDKDriver(RobotDriver):
    """RoboMaster SDK-based robot driver."""
    
    def __init__(self):
        self._robot = None
        self._chassis = None
        self._chassis_controller = None
        self._arm = None
        self._arm_controller = None
        self._gripper = None
        self._camera = None
        self._connected = False
        self._led_on = False
        
        # Position subscription
        self._position_callback = None
        self._current_position = (0.0, 0.0, 0.0)  # x, y, z(yaw)
    
    def connect(self, local_ip: Optional[str] = None, robot_ip: Optional[str] = None, 
                verbose: bool = True) -> bool:
        """Connect to robot using SDK.
        
        Uses the same connection logic as cli/connection.py.
        
        Args:
            local_ip: Local IP address (default: 192.168.2.20)
            robot_ip: Robot IP address (default: 192.168.2.1)
            verbose: Print connection info
        """
        from robomaster import robot, config
        
        # Configure SDK IP addresses (same as cli/connection.py)
        configure_ips(local_ip, robot_ip)
        
        if verbose:
            print(f"  Local IP: {config.LOCAL_IP_STR}")
            print(f"  Robot IP: {config.ROBOT_IP_STR}")
        
        self._robot = robot.Robot()
        
        try:
            self._robot.initialize(conn_type="sta")
            
            self._chassis = self._robot.chassis
            self._chassis_controller = SDKChassisController(self._chassis)
            
            # Set stick overlay mode
            try:
                self._chassis.stick_overlay(fusion_mode=STICK_OVERLAY_MODE)
            except:
                pass
            
            # Try to get arm
            try:
                self._arm = self._robot.robotic_arm
                self._arm_controller = SDKArmController(self._arm)
            except:
                self._arm = None
                self._arm_controller = None
            
            # Try to get gripper
            try:
                self._gripper = self._robot.gripper
            except:
                self._gripper = None
            
            self._connected = True
            return True
            
        except Exception as e:
            self._connected = False
            raise RuntimeError(f"Failed to connect: {e}")
    
    def disconnect(self):
        """Disconnect from robot."""
        self.stop()
        self.stop_video()
        
        if self._gripper:
            try:
                self._gripper.pause()
            except:
                pass
        
        if self._robot:
            try:
                self._robot.close()
            except:
                pass
        
        self._connected = False
    
    def get_status(self) -> RobotStatus:
        """Get current status."""
        return RobotStatus(
            connected=self._connected,
            arm_ready=self._arm_controller.is_ready() if self._arm_controller else True,
            arm_status=self._arm_controller.get_status() if self._arm_controller else "N/A",
            gripper_open=True,  # SDK doesn't expose this easily
            battery=None,
        )
    
    # --- Chassis control ---
    
    def drive_speed(self, vx: float, vy: float, vz: float, timeout: float = 0.5):
        """Set chassis speed."""
        if self._chassis:
            try:
                self._chassis.drive_speed(x=vx, y=vy, z=vz, timeout=timeout)
            except:
                pass
    
    def drive_move(self, x: float, y: float, z: float, 
                   xy_speed: float = 0.5, z_speed: float = 60) -> bool:
        """Move chassis by distance (uses action tracking)."""
        if self._chassis_controller:
            return self._chassis_controller.move(x, y, z, xy_speed, z_speed)
        return False
    
    def is_chassis_ready(self) -> bool:
        """Check if chassis is ready for new step move command."""
        if self._chassis_controller:
            return self._chassis_controller.is_ready()
        return True
    
    def stop(self):
        """Stop all movement."""
        if self._chassis:
            for _ in range(3):
                try:
                    self._chassis.drive_speed(x=0, y=0, z=0)
                    break
                except:
                    pass
    
    # --- Arm control ---
    
    def arm_move(self, x: float, y: float) -> bool:
        """Move robotic arm."""
        if self._arm_controller:
            return self._arm_controller.move(x=x, y=y)
        return False
    
    def is_arm_ready(self) -> bool:
        """Check if arm is ready."""
        if self._arm_controller:
            return self._arm_controller.is_ready()
        return True
    
    def arm_recenter(self) -> bool:
        """Move arm to center/home position."""
        if self._arm and self._arm_controller and self._arm_controller.is_ready():
            try:
                action = self._arm.recenter()
                return self._arm_controller.execute_move(action)
            except Exception as e:
                self._arm_controller._set_status(f"Recenter error: {e}", is_moving=False)
        return False
    
    # --- Gripper control ---
    
    def gripper_open(self, power: int = 50):
        """Open gripper."""
        if self._gripper:
            try:
                self._gripper.open(power=power)
            except:
                pass
    
    def gripper_close(self, power: int = 50):
        """Close gripper."""
        if self._gripper:
            try:
                self._gripper.close(power=power)
            except:
                pass
    
    def gripper_stop(self):
        """Stop gripper."""
        if self._gripper:
            try:
                self._gripper.pause()
            except:
                pass
    
    # --- LED control ---
    
    def led_on(self, r: int = 255, g: int = 255, b: int = 255):
        """Turn on all LEDs with specified color."""
        if self._robot:
            try:
                led = self._robot.led
                # Set all LED components
                led.set_led(comp="all", r=r, g=g, b=b, effect="on")
                self._led_on = True
            except Exception:
                pass
    
    def led_off(self):
        """Turn off all LEDs."""
        if self._robot:
            try:
                led = self._robot.led
                led.set_led(comp="all", r=0, g=0, b=0, effect="off")
                self._led_on = False
            except Exception:
                pass
    
    def led_toggle(self, r: int = 255, g: int = 255, b: int = 255) -> bool:
        """Toggle LEDs on/off."""
        if self._led_on:
            self.led_off()
            return False
        else:
            self.led_on(r, g, b)
            return True
    
    # --- Video ---
    
    def start_video(self, resolution: str = '360p') -> bool:
        """Start video stream."""
        try:
            from robomaster import camera
            
            res_map = {
                '360p': camera.STREAM_360P,
                '540p': camera.STREAM_540P,
                '720p': camera.STREAM_720P,
            }
            
            self._camera = self._robot.camera
            self._camera.start_video_stream(display=False, resolution=res_map.get(resolution))
            return True
        except Exception:
            self._camera = None
            return False
    
    def stop_video(self):
        """Stop video stream."""
        if self._camera:
            try:
                self._camera.stop_video_stream()
            except:
                pass
            self._camera = None
    
    def get_video_frame(self) -> Optional[np.ndarray]:
        """Get current video frame."""
        if self._camera:
            try:
                return self._camera.read_cv2_image(strategy="newest", timeout=0.1)
            except:
                return None
        return None
    
    # --- Properties for direct access if needed ---
    
    @property
    def has_arm(self) -> bool:
        return self._arm is not None
    
    @property
    def has_gripper(self) -> bool:
        return self._gripper is not None
    
    @property
    def arm_status(self) -> str:
        if self._arm_controller:
            return self._arm_controller.get_status()
        return "N/A"
    
    # --- Position subscription ---
    
    def _position_handler(self, x: float, y: float, z: float):
        """Internal handler for position subscription callback."""
        self._current_position = (x, y, z)
        if self._position_callback:
            self._position_callback(x, y, z)
    
    def subscribe_position(self, callback=None, freq: int = 10) -> bool:
        """Subscribe to chassis position updates.
        
        Args:
            callback: Optional callback function(x, y, z) in meters, degrees
            freq: Update frequency in Hz (default 10)
            
        Returns:
            True if subscription successful
        """
        if self._chassis:
            try:
                self._position_callback = callback
                self._chassis.sub_position(freq=freq, callback=self._position_handler)
                return True
            except Exception:
                return False
        return False
    
    def unsubscribe_position(self):
        """Unsubscribe from chassis position updates."""
        if self._chassis:
            try:
                self._chassis.unsub_position()
            except:
                pass
        self._position_callback = None
    
    @property
    def current_position(self) -> tuple:
        """Get current position (x, y, z) from subscription."""
        return self._current_position
