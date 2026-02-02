"""
Command recorder for drive sessions.

Records all robot commands (chassis, arm, gripper) with timestamps
for later replay. Saves to JSON format for easy parsing.
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional


class CommandRecorder:
    """Records robot commands with timestamps and position state."""
    
    def __init__(self, output_path: Optional[str] = None):
        """Initialize recorder.
        
        Args:
            output_path: Path to save recording. If None, auto-generates name.
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"recording_{timestamp}.json"
        
        self.output_path = Path(output_path)
        self.commands = []
        self.start_time = None
        self._recording = False
        
        # Current position state from subscription
        self._position = (0.0, 0.0, 0.0)  # (x, y, z/yaw)
    
    def update_position(self, x: float, y: float, z: float):
        """Update current position from chassis subscription.
        
        Args:
            x: X position in meters
            y: Y position in meters
            z: Yaw angle in degrees
        """
        self._position = (x, y, z)
    
    def start(self):
        """Start recording."""
        self.commands = []
        self.start_time = time.time()
        self._recording = True
    
    def stop(self):
        """Stop recording."""
        self._recording = False
    
    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recording
    
    def _timestamp(self) -> float:
        """Get current timestamp relative to start."""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time
    
    def record_chassis_speed(self, vx: float, vy: float, vz: float):
        """Record chassis speed command with expected position."""
        if not self._recording:
            return
        
        self.commands.append({
            'time': self._timestamp(),
            'type': 'chassis_speed',
            'vx': vx,
            'vy': vy,
            'vz': vz,
            'expected_pos': {
                'x': self._position[0],
                'y': self._position[1],
                'z': self._position[2],
            }
        })
    
    def record_chassis_move(self, x: float, y: float, z: float, 
                            xy_speed: float, z_speed: float):
        """Record chassis move command with expected position."""
        if not self._recording:
            return
        
        self.commands.append({
            'time': self._timestamp(),
            'type': 'chassis_move',
            'x': x,
            'y': y,
            'z': z,
            'xy_speed': xy_speed,
            'z_speed': z_speed,
            'expected_pos': {
                'x': self._position[0],
                'y': self._position[1],
                'z': self._position[2],
            }
        })
    
    def record_arm_move(self, x: float, y: float):
        """Record arm move command."""
        if not self._recording:
            return
        
        self.commands.append({
            'time': self._timestamp(),
            'type': 'arm_move',
            'x': x,
            'y': y,
        })
    
    def record_arm_recenter(self):
        """Record arm recenter command."""
        if not self._recording:
            return
        
        self.commands.append({
            'time': self._timestamp(),
            'type': 'arm_recenter',
        })
    
    def record_gripper_open(self, power: int):
        """Record gripper open command."""
        if not self._recording:
            return
        
        self.commands.append({
            'time': self._timestamp(),
            'type': 'gripper_open',
            'power': power,
        })
    
    def record_gripper_close(self, power: int):
        """Record gripper close command."""
        if not self._recording:
            return
        
        self.commands.append({
            'time': self._timestamp(),
            'type': 'gripper_close',
            'power': power,
        })
    
    def record_gripper_stop(self):
        """Record gripper stop command."""
        if not self._recording:
            return
        
        self.commands.append({
            'time': self._timestamp(),
            'type': 'gripper_stop',
        })
    
    def record_stop(self):
        """Record stop command."""
        if not self._recording:
            return
        
        self.commands.append({
            'time': self._timestamp(),
            'type': 'stop',
        })
    
    def save(self) -> str:
        """Save recording to file.
        
        Returns:
            str: Path to saved file
        """
        # Optimize: remove redundant commands (consecutive identical speed commands)
        optimized = self._optimize_commands()
        
        data = {
            'version': '1.0',
            'recorded_at': datetime.now().isoformat(),
            'duration': self._timestamp() if self.start_time else 0,
            'command_count': len(optimized),
            'commands': optimized,
        }
        
        with open(self.output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        return str(self.output_path)
    
    def _optimize_commands(self) -> list:
        """Remove redundant consecutive commands."""
        if not self.commands:
            return []
        
        optimized = [self.commands[0]]
        last_speed = None
        last_gripper = None
        
        for cmd in self.commands[1:]:
            # Skip redundant chassis_speed commands
            if cmd['type'] == 'chassis_speed':
                speed_key = (cmd['vx'], cmd['vy'], cmd['vz'])
                if speed_key == last_speed:
                    continue
                last_speed = speed_key
            
            # Skip redundant gripper commands
            elif cmd['type'] in ('gripper_open', 'gripper_close', 'gripper_stop'):
                if cmd['type'] == last_gripper:
                    continue
                last_gripper = cmd['type']
            
            optimized.append(cmd)
        
        return optimized


def load_recording(path: str) -> dict:
    """Load a recording from file.
    
    Args:
        path: Path to recording JSON file
        
    Returns:
        dict: Recording data with 'commands' list
    """
    with open(path, 'r') as f:
        return json.load(f)


class CommandPlayer:
    """Plays back recorded commands to a robot driver with position verification."""
    
    POSITION_TOLERANCE = 0.01  # 1% tolerance (99% accuracy)
    
    def __init__(self, recording_path: str):
        """Initialize player with recording file.
        
        Args:
            recording_path: Path to JSON recording file
        """
        self.recording = load_recording(recording_path)
        self.commands = self.recording.get('commands', [])
        self.duration = self.recording.get('duration', 0)
        self.current_index = 0
        self.start_time = None
        self._stopped = False
        
        # Current position from subscription
        self._current_position = (0.0, 0.0, 0.0)
        
        # Track if we're waiting for position
        self._waiting_for_position = False
        self._target_position = None
    
    def update_position(self, x: float, y: float, z: float):
        """Update current position from chassis subscription.
        
        Args:
            x: X position in meters
            y: Y position in meters
            z: Yaw angle in degrees
        """
        self._current_position = (x, y, z)
    
    def start(self):
        """Start playback."""
        self.start_time = time.time()
        self.current_index = 0
        self._stopped = False
    
    def stop(self):
        """Stop playback."""
        self._stopped = True
    
    @property
    def is_playing(self) -> bool:
        """Check if playback is active."""
        return (self.start_time is not None and 
                not self._stopped and 
                self.current_index < len(self.commands))
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time since start."""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time
    
    @property
    def progress(self) -> float:
        """Get progress as percentage (0-100)."""
        if self.duration <= 0:
            return 100.0
        return min(100.0, (self.elapsed / self.duration) * 100)
    
    def get_pending_commands(self) -> list:
        """Get commands that should be executed now.
        
        Returns:
            list: Commands whose time has passed
        """
        if not self.is_playing:
            return []
        
        current_time = self.elapsed
        pending = []
        
        while (self.current_index < len(self.commands) and 
               self.commands[self.current_index]['time'] <= current_time):
            pending.append(self.commands[self.current_index])
            self.current_index += 1
        
        return pending
    
    def execute_command(self, cmd: dict, driver):
        """Execute a single command on the driver.
        
        Args:
            cmd: Command dictionary with 'type' and parameters
            driver: RobotDriver instance
        """
        cmd_type = cmd.get('type')
        
        if cmd_type == 'chassis_speed':
            driver.drive_speed(cmd['vx'], cmd['vy'], cmd['vz'])
        
        elif cmd_type == 'chassis_move':
            driver.drive_move(cmd['x'], cmd['y'], cmd['z'],
                            cmd.get('xy_speed', 0.5), cmd.get('z_speed', 60))
        
        elif cmd_type == 'arm_move':
            driver.arm_move(cmd['x'], cmd['y'])
        
        elif cmd_type == 'arm_recenter':
            driver.arm_recenter()
        
        elif cmd_type == 'gripper_open':
            driver.gripper_open(cmd.get('power', 50))
        
        elif cmd_type == 'gripper_close':
            driver.gripper_close(cmd.get('power', 50))
        
        elif cmd_type == 'gripper_stop':
            driver.gripper_stop()
        
        elif cmd_type == 'stop':
            driver.stop()
    
    def check_position_reached(self, expected_pos: dict) -> bool:
        """Check if current position is within tolerance of expected position.
        
        Args:
            expected_pos: Dict with 'x', 'y', 'z' keys (meters, meters, degrees)
            
        Returns:
            True if within 99% of expected position
        """
        if expected_pos is None:
            return True
        
        exp_x = expected_pos.get('x', 0.0)
        exp_y = expected_pos.get('y', 0.0)
        exp_z = expected_pos.get('z', 0.0)
        
        cur_x, cur_y, cur_z = self._current_position
        
        # Calculate distance error for x, y (in meters)
        # Use absolute tolerance for position (1cm = 0.01m is 99% of 1m movements)
        xy_tolerance = 0.01  # 1cm tolerance
        z_tolerance = 1.0    # 1 degree tolerance
        
        dx = abs(cur_x - exp_x)
        dy = abs(cur_y - exp_y)
        dz = abs(cur_z - exp_z)
        
        # Normalize yaw difference to -180 to 180
        while dz > 180:
            dz -= 360
        dz = abs(dz)
        
        return dx <= xy_tolerance and dy <= xy_tolerance and dz <= z_tolerance
    
    def get_next_command_with_position(self) -> Optional[dict]:
        """Get next command if position matches, None if need to wait.
        
        Returns:
            Next command if current position matches expected, None otherwise
        """
        if not self.is_playing:
            return None
        
        if self.current_index >= len(self.commands):
            return None
        
        cmd = self.commands[self.current_index]
        expected_pos = cmd.get('expected_pos')
        
        # If command has expected position, verify we're there
        if expected_pos and not self.check_position_reached(expected_pos):
            return None  # Not ready yet, keep waiting
        
        # Position matched or no position required, return command
        self.current_index += 1
        return cmd
    
    @property
    def current_position(self) -> tuple:
        """Get current position."""
        return self._current_position
    
    @property
    def is_waiting_for_position(self) -> bool:
        """Check if waiting for position to match."""
        if not self.is_playing or self.current_index >= len(self.commands):
            return False
        
        cmd = self.commands[self.current_index]
        expected_pos = cmd.get('expected_pos')
        if expected_pos:
            return not self.check_position_reached(expected_pos)
        return False
