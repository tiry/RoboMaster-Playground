"""
Telemetry display for robot sensor data.

Opens a separate OpenCV window showing real-time telemetry data from
chassis, arm, and gripper subscriptions.
"""

import cv2
import numpy as np
import threading
import time as time_module
from typing import Optional, Dict, Any
from .config import TELEMETRY


class TelemetryData:
    """Stores the latest telemetry values from subscriptions."""
    
    def __init__(self):
        # Chassis position (x, y, z/yaw in meters/degrees)
        self.position = (0.0, 0.0, 0.0)
        
        # Chassis attitude (yaw, pitch, roll in degrees)
        self.attitude = (0.0, 0.0, 0.0)
        
        # Chassis velocity (vgx, vgy, vgz, vbx, vby, vbz)
        self.velocity = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        
        # IMU data (acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z)
        self.imu = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        
        # Chassis status (static, uphill, downhill, etc.)
        self.status = ()
        
        # Arm position (x, y in mm)
        self.arm_position = (0.0, 0.0)
        
        # Gripper status
        self.gripper_status = (0, 0)
        
        # Lock for thread-safe access
        self._lock = threading.Lock()
        
        # Update counter and last update time (for debug)
        self._update_count = 0
        self._last_update = time_module.time()
    
    def update_position(self, x: float, y: float, z: float):
        with self._lock:
            self.position = (x, y, z)
            self._update_count += 1
            self._last_update = time_module.time()
    
    def update_attitude(self, yaw: float, pitch: float, roll: float):
        with self._lock:
            self.attitude = (yaw, pitch, roll)
            self._update_count += 1
            self._last_update = time_module.time()
    
    def update_velocity(self, *args):
        with self._lock:
            self.velocity = args
            self._update_count += 1
            self._last_update = time_module.time()
    
    def update_status(self, *args):
        with self._lock:
            self.status = args
            self._update_count += 1
            self._last_update = time_module.time()
    
    def update_arm_position(self, x: float, y: float):
        with self._lock:
            self.arm_position = (x, y)
            self._update_count += 1
            self._last_update = time_module.time()
    
    def update_gripper_status(self, *args):
        with self._lock:
            self.gripper_status = args
            self._update_count += 1
            self._last_update = time_module.time()
    
    def update_imu(self, *args):
        with self._lock:
            self.imu = args
            self._update_count += 1
            self._last_update = time_module.time()
    
    def get_all(self) -> Dict[str, Any]:
        """Get all telemetry data as a dictionary (thread-safe)."""
        with self._lock:
            return {
                'position': self.position,
                'attitude': self.attitude,
                'velocity': self.velocity,
                'imu': self.imu,
                'status': self.status,
                'arm_position': self.arm_position,
                'gripper_status': self.gripper_status,
                'update_count': self._update_count,
                'last_update': self._last_update,
            }


class TelemetryDisplay:
    """Displays telemetry data in a separate OpenCV window."""
    
    WINDOW_NAME = "RoboMaster Telemetry"
    
    # Status labels for chassis status tuple
    STATUS_LABELS = ['static', 'uphill', 'downhill', 'on_slope', 
                     'pick_up', 'slip', 'impact', 'hill_static', 'hill_err']
    
    def __init__(self, width: int = None, height: int = None):
        """Initialize telemetry display.
        
        Args:
            width: Window width (default from TELEMETRY config)
            height: Window height (default from TELEMETRY config)
        """
        self.width = width or TELEMETRY.get('window_width', 400)
        self.height = height or TELEMETRY.get('window_height', 500)
        self.data = TelemetryData()
        self._running = False
        self._video_width = 0
        self._window_positioned = False
    
    def start(self, video_width: int = 0):
        """Start the telemetry display.
        
        Args:
            video_width: Width of video window (if present) to position telemetry next to it
        """
        self._running = True
        self._video_width = video_width
        self._window_positioned = False
    
    def stop(self):
        """Stop the telemetry display."""
        self._running = False
        try:
            cv2.destroyWindow(self.WINDOW_NAME)
        except:
            pass
    
    def update(self):
        """Update the telemetry window. Call this in the main loop."""
        if not self._running:
            return
        
        # Create black background
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Get current data
        data = self.data.get_all()
        
        y = 30
        line_height = 22
        section_gap = 10
        
        # Title
        cv2.putText(img, "TELEMETRY", (10, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        y += line_height + section_gap
        
        # === Position ===
        cv2.putText(img, "Position", (10, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        y += line_height
        pos = data['position']
        cv2.putText(img, f"  X: {pos[0]:+.2f} m  Y: {pos[1]:+.2f} m  Yaw: {pos[2]:+.2f}d", (10, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        y += line_height + section_gap
        
        # === Attitude ===
        cv2.putText(img, "Attitude", (10, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        y += line_height
        att = data['attitude']
        cv2.putText(img, f"  Yaw: {att[0]:+.2f}d  Pitch: {att[1]:+.2f}d  Roll: {att[2]:+.2f}d", (10, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        y += line_height + section_gap
        
        # === Velocity ===
        cv2.putText(img, "Velocity", (10, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        y += line_height
        vel = data['velocity']
        if len(vel) >= 2:
            # Linear velocity from sub_velocity
            cv2.putText(img, f"  vx: {vel[0]:+.2f} m/s  vy: {vel[1]:+.2f} m/s", (10, y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            y += line_height
        y += section_gap
        
        # === IMU / Gyroscope ===
        cv2.putText(img, "IMU", (10, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        y += line_height
        imu = data['imu']
        if len(imu) >= 6:
            # Accelerometer (m/s²)
            cv2.putText(img, f"  Accel: x={imu[0]:+.2f} y={imu[1]:+.2f} z={imu[2]:+.2f}", (10, y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            y += line_height
            # Gyroscope - convert from rad/s to deg/s (multiply by 57.3)
            RAD_TO_DEG = 57.2957795
            gx = imu[3] * RAD_TO_DEG
            gy = imu[4] * RAD_TO_DEG
            gz = imu[5] * RAD_TO_DEG
            cv2.putText(img, f"  Gyro:  x={gx:+.2f} y={gy:+.2f} z={gz:+.2f} deg/s", (10, y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            y += line_height
        y += section_gap
        
        # === Arm Position ===
        cv2.putText(img, "Robotic Arm", (10, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        y += line_height
        arm = data['arm_position']
        cv2.putText(img, f"  X: {arm[0]:+.2f} mm  Y: {arm[1]:+.2f} mm", (10, y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        y += line_height + section_gap
        
        # Show update stats
        freq = TELEMETRY.get('frequency', 50)
        update_count = data.get('update_count', 0)
        last_update = data.get('last_update', 0)
        age = time_module.time() - last_update if last_update > 0 else 999
        
        # Show update count and age (green if recent, red if stale)
        if age < 1.0:
            age_color = (0, 255, 0)  # Green - recent
        elif age < 5.0:
            age_color = (0, 255, 255)  # Yellow - getting stale
        else:
            age_color = (0, 0, 255)  # Red - stale
        
        cv2.putText(img, f"Updates: {update_count}  Age: {age:.1f}s", (10, self.height - 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, age_color, 1)
        cv2.putText(img, f"Target: {freq} Hz", (10, self.height - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (128, 128, 128), 1)
        
        # Display
        cv2.imshow(self.WINDOW_NAME, img)
        
        # Position window next to video on first display
        if not self._window_positioned:
            if self._video_width > 0:
                # Place telemetry window to the right of video window
                # Video is at (50, 100), so telemetry goes at (50 + video_width + gap, 100)
                telemetry_x = 50 + self._video_width + 10
                telemetry_y = 100
            else:
                # No video - place at top-left
                telemetry_x = 50
                telemetry_y = 100
            cv2.moveWindow(self.WINDOW_NAME, telemetry_x, telemetry_y)
            self._window_positioned = True


def setup_telemetry_subscriptions(driver, telemetry: TelemetryDisplay, freq: int = None):
    """Subscribe to all telemetry sources.
    
    Args:
        driver: SDKDriver instance
        telemetry: TelemetryDisplay instance
        freq: Subscription frequency in Hz (default from TELEMETRY config)
    
    Returns:
        bool: True if all subscriptions successful
    """
    freq = freq or TELEMETRY.get('frequency', 50)
    success_count = 0
    total_count = 0
    
    # Use wrapper functions to ensure correct callback signatures
    data = telemetry.data
    
    # Subscribe to chassis position
    # cs=0: relative to current position, cs=1: relative to power-on position
    total_count += 1
    try:
        def position_cb(pos_tuple):
            # DEBUG: Print first 10 position callbacks
            if data._update_count < 30:
                print(f"  [DEBUG] Position raw: {pos_tuple}, type={type(pos_tuple)}, len={len(pos_tuple) if hasattr(pos_tuple, '__len__') else 'N/A'}")
            # SDK callback format: (x, y, z) - 3 values
            if isinstance(pos_tuple, tuple) and len(pos_tuple) >= 3:
                data.update_position(pos_tuple[0], pos_tuple[1], pos_tuple[2])
        # Use cs=1 for power-on reference frame
        driver._chassis.sub_position(cs=1, freq=freq, callback=position_cb)
        print(f"  ✓ Position subscription OK (cs=1: power-on reference)")
        success_count += 1
    except Exception as e:
        print(f"  ⚠️  Position subscription failed: {e}")
    
    # Subscribe to chassis attitude
    total_count += 1
    try:
        def attitude_cb(att_tuple):
            # SDK sends ((yaw, pitch, roll),)
            if isinstance(att_tuple, tuple) and len(att_tuple) >= 3:
                data.update_attitude(att_tuple[0], att_tuple[1], att_tuple[2])
        driver._chassis.sub_attitude(freq=freq, callback=attitude_cb)
        print(f"  ✓ Attitude subscription OK")
        success_count += 1
    except Exception as e:
        print(f"  ⚠️  Attitude subscription failed: {e}")
    
    # Subscribe to chassis velocity
    # SDK sub_velocity returns (vgx, vgy, vgz, vbx, vby, vbz) where vgz/vbz = vertical (always 0)
    total_count += 1
    try:
        def velocity_cb(vel_tuple):
            # SDK returns 6 elements for linear velocity
            if isinstance(vel_tuple, tuple):
                data.update_velocity(*vel_tuple)
        driver._chassis.sub_velocity(freq=freq, callback=velocity_cb)
        print(f"  ✓ Velocity subscription OK")
        success_count += 1
    except Exception as e:
        print(f"  ⚠️  Velocity subscription failed: {e}")
    
    # Subscribe to IMU data for angular velocity (gyroscope)
    # SDK sub_imu returns (acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z)
    total_count += 1
    try:
        def imu_cb(imu_tuple):
            # SDK returns (acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z)
            if isinstance(imu_tuple, tuple):
                data.update_imu(*imu_tuple)
        driver._chassis.sub_imu(freq=freq, callback=imu_cb)
        print(f"  ✓ IMU subscription OK (gyro_z = angular velocity)")
        success_count += 1
    except Exception as e:
        print(f"  ⚠️  IMU subscription failed: {e}")
    
    # Subscribe to arm position (if available) - SDK sends as tuple-in-tuple
    if driver._arm:
        total_count += 1
        try:
            def arm_cb(arm_tuple):
                # SDK likely sends ((x, y),) - extract inner tuple
                if isinstance(arm_tuple, tuple) and len(arm_tuple) >= 2:
                    data.update_arm_position(arm_tuple[0], arm_tuple[1])
            driver._arm.sub_position(freq=freq, callback=arm_cb)
            print(f"  ✓ Arm position subscription OK")
            success_count += 1
        except Exception as e:
            print(f"  ⚠️  Arm subscription failed: {e}")
    
    # Status and Gripper subscriptions removed (not useful)
    
    print(f"  Subscriptions: {success_count}/{total_count} successful")
    return success_count == total_count


def cleanup_telemetry_subscriptions(driver):
    """Unsubscribe from all telemetry sources.
    
    Args:
        driver: SDKDriver instance
    """
    try:
        driver._chassis.unsub_position()
    except:
        pass
    
    try:
        driver._chassis.unsub_attitude()
    except:
        pass
    
    try:
        driver._chassis.unsub_velocity()
    except:
        pass
    
    try:
        driver._chassis.unsub_imu()
    except:
        pass
    
    if driver._arm:
        try:
            driver._arm.unsub_position()
        except:
            pass
