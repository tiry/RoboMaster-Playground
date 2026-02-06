"""
LeRobot-based recording for VLA training datasets.

This module provides:
- FrameBuffer: Thread-safe ring buffer for frames and commands
- LeRobotRecorder: Recording logic with LeRobot dataset format
- normalize_action/denormalize_action: Action normalization functions
"""

import time
import threading
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

from .config import LEROBOT, WEBCAM, ROBOT_VIDEO

# Action names in order for the action tensor
ACTION_NAMES = [
    'move_x', 'move_y', 'rotate_z', 
    'gripper_open', 'gripper_close', 'arm_recenter',
    'arm_x', 'arm_y', 'unused'
]


def normalize_action(raw_actions: dict, action_ranges: dict = None) -> List[float]:
    """Convert raw action values to normalized [-1, 1] tensor.
    
    Args:
        raw_actions: Dict with raw values {'move_x': 0.5, 'gripper_open': 50, ...}
        action_ranges: Dict of (min, max) tuples. If None, uses LEROBOT config.
        
    Returns:
        List of 9 normalized float32 values
    """
    if action_ranges is None:
        action_ranges = LEROBOT.get('action_ranges', {})
    
    normalized = []
    for name in ACTION_NAMES:
        if name == 'unused':
            normalized.append(0.0)
            continue
            
        raw_value = raw_actions.get(name, 0.0)
        min_val, max_val = action_ranges.get(name, (0, 1))
        
        # Clip to range and normalize to [-1, 1]
        clipped = max(min_val, min(max_val, raw_value))
        if max_val - min_val > 0:
            norm = (clipped - min_val) / (max_val - min_val) * 2 - 1
        else:
            norm = 0.0
        normalized.append(float(norm))
    
    return normalized


def denormalize_action(normalized_actions: List[float], action_ranges: dict = None) -> dict:
    """Convert normalized [-1, 1] tensor back to raw action values.
    
    Args:
        normalized_actions: List of 9 normalized values
        action_ranges: Dict of (min, max) tuples. If None, uses LEROBOT config.
        
    Returns:
        Dict with raw values {'move_x': 0.5, 'gripper_open': 50, ...}
    """
    if action_ranges is None:
        action_ranges = LEROBOT.get('action_ranges', {})
    
    raw_actions = {}
    for i, name in enumerate(ACTION_NAMES):
        if name == 'unused':
            continue
        
        if i < len(normalized_actions):
            norm_value = normalized_actions[i]
        else:
            norm_value = 0.0
            
        min_val, max_val = action_ranges.get(name, (0, 1))
        
        # Denormalize from [-1, 1] to raw range
        raw = (norm_value + 1) / 2 * (max_val - min_val) + min_val
        raw_actions[name] = raw
    
    return raw_actions


class FrameBuffer:
    """Thread-safe ring buffer for frames and commands."""
    
    def __init__(self, max_duration: float = None, fps: int = None):
        """Initialize the frame buffer.
        
        Args:
            max_duration: Maximum buffer duration in seconds. Default from config.
            fps: Recording FPS. Default from config.
        """
        max_duration = max_duration or LEROBOT.get('buffer_duration', 2.0)
        fps = fps or LEROBOT.get('default_fps', 30)
        
        self.fps = fps
        self.max_frames = int(max_duration * fps)
        
        # Frame buffers: (timestamp, frame)
        self.robot_frames: deque = deque(maxlen=self.max_frames)
        self.webcam_frames: deque = deque(maxlen=self.max_frames)
        
        # Command buffer: (timestamp, command_dict)
        # More commands than frames since commands come faster
        self.commands: deque = deque(maxlen=self.max_frames * 10)
        
        self._lock = threading.Lock()
        self._last_processed_time = 0.0
    
    def add_robot_frame(self, frame: np.ndarray, timestamp: float = None):
        """Add a robot camera frame to the buffer."""
        if timestamp is None:
            timestamp = time.time()
        with self._lock:
            self.robot_frames.append((timestamp, frame.copy()))
    
    def add_webcam_frame(self, frame: np.ndarray, timestamp: float = None):
        """Add a webcam frame to the buffer."""
        if timestamp is None:
            timestamp = time.time()
        with self._lock:
            self.webcam_frames.append((timestamp, frame.copy()))
    
    def add_command(self, command: dict, timestamp: float = None):
        """Add a command to the buffer.
        
        Args:
            command: Dict like {'move_x': 0.5, 'gripper_open': 50}
            timestamp: Time of command. If None, uses current time.
        """
        if timestamp is None:
            timestamp = time.time()
        with self._lock:
            self.commands.append((timestamp, command.copy()))
    
    def get_frame_at_time(self, target_time: float, source: str, offset: float = 0.0) -> Optional[np.ndarray]:
        """Get frame closest to target_time + offset.
        
        Args:
            target_time: Target timestamp
            source: 'robot' or 'webcam'
            offset: Time offset in seconds (from config)
            
        Returns:
            Frame array or None if no frames available
        """
        with self._lock:
            frames = self.robot_frames if source == 'robot' else self.webcam_frames
            
            if not frames:
                return None
            
            adjusted_time = target_time + offset
            
            # Find closest frame
            best_frame = None
            best_diff = float('inf')
            
            for ts, frame in frames:
                diff = abs(ts - adjusted_time)
                if diff < best_diff:
                    best_diff = diff
                    best_frame = frame
            
            return best_frame
    
    def aggregate_commands(self, start_time: float, end_time: float) -> dict:
        """Aggregate all commands between start and end time.
        
        Rules:
        - Numeric values (move_x, move_y, rotate_z, gripper_open, gripper_close, arm_x, arm_y): SUM
        - Boolean values (arm_recenter): OR (1 if any True)
        
        Args:
            start_time: Start timestamp (exclusive)
            end_time: End timestamp (inclusive)
            
        Returns:
            Dict with aggregated raw action values
        """
        # Initialize aggregated values
        aggregated = {name: 0.0 for name in ACTION_NAMES if name != 'unused'}
        
        with self._lock:
            for ts, cmd in self.commands:
                if start_time < ts <= end_time:
                    for key, value in cmd.items():
                        if key in aggregated:
                            if key == 'arm_recenter':
                                # Boolean OR: if any is True (1), result is 1
                                if value:
                                    aggregated[key] = 1.0
                            else:
                                # Numeric SUM
                                aggregated[key] += value
        
        # Clip gripper values to max 100
        action_ranges = LEROBOT.get('action_ranges', {})
        for key in ['gripper_open', 'gripper_close']:
            if key in aggregated:
                min_val, max_val = action_ranges.get(key, (0, 100))
                aggregated[key] = max(min_val, min(max_val, aggregated[key]))
        
        return aggregated
    
    def clear(self):
        """Clear all buffers."""
        with self._lock:
            self.robot_frames.clear()
            self.webcam_frames.clear()
            self.commands.clear()
            self._last_processed_time = 0.0


class LeRobotRecorder:
    """Records teleoperation data in LeRobot dataset format."""
    
    def __init__(self, fps: int = None, task: str = None, dry_run: bool = False):
        """Initialize the LeRobot recorder.
        
        Args:
            fps: Recording FPS. Default from config.
            task: Episode task description. Default from config.
            dry_run: If True, prints frame info instead of saving.
        """
        self.fps = fps or LEROBOT.get('default_fps', 30)
        self.task = task or LEROBOT.get('default_task', 'do something with Robomaster')
        self.dry_run = dry_run
        
        self.buffer = FrameBuffer(fps=self.fps)
        self.frame_interval = 1.0 / self.fps
        
        # Recording state
        self._recording = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._frame_count = 0
        self._start_time = 0.0
        self._last_frame_time = 0.0
        
        # LeRobot dataset (created on start)
        self._dataset = None
        
        # Camera offsets
        self._robot_offset = LEROBOT.get('robot_camera_offset', 0.0)
        self._webcam_offset = LEROBOT.get('static_camera_offset', 0.0)
    
    @property
    def is_recording(self) -> bool:
        """Check if recording is active."""
        return self._recording
    
    @property
    def frame_count(self) -> int:
        """Get current frame count."""
        return self._frame_count
    
    def start(self):
        """Start recording in a background thread."""
        if self._recording:
            return
        
        self._recording = True
        self._frame_count = 0
        self._start_time = time.time()
        self._last_frame_time = self._start_time
        self._stop_event.clear()
        self.buffer.clear()
        
        if not self.dry_run:
            self._init_dataset()
        
        # Start recording thread
        self._thread = threading.Thread(target=self._recording_loop, daemon=True)
        self._thread.start()
    
    def stop(self) -> bool:
        """Stop recording.
        
        Returns:
            True if episode was saved, False if aborted or dry run.
        """
        if not self._recording:
            return False
        
        self._recording = False
        self._stop_event.set()
        
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        
        if self.dry_run:
            print(f"\n[DRY RUN] Would have saved {self._frame_count} frames")
            return False
        
        return self._save_episode()
    
    def abort(self):
        """Abort recording without saving."""
        self._recording = False
        self._stop_event.set()
        
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        
        self._dataset = None
        print(f"\n[ABORT] Recording aborted ({self._frame_count} frames discarded)")
    
    def add_robot_frame(self, frame: np.ndarray):
        """Add a robot camera frame (call from main thread)."""
        if self._recording:
            self.buffer.add_robot_frame(frame)
    
    def add_webcam_frame(self, frame: np.ndarray):
        """Add a webcam frame (call from main thread)."""
        if self._recording:
            self.buffer.add_webcam_frame(frame)
    
    def add_command(self, command: dict):
        """Add a command (call from main thread).
        
        Args:
            command: Dict like {'move_x': 0.5, 'gripper_open': 50}
        """
        if self._recording:
            self.buffer.add_command(command)
    
    def _init_dataset(self):
        """Initialize LeRobot dataset."""
        try:
            import torch
            from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
            
            dataset_root = Path(LEROBOT.get('dataset_root', './records')).expanduser()
            dataset_name = LEROBOT.get('dataset_name', 'robomaster_teleop')
            
            # Get video dimensions from config
            webcam_height = WEBCAM.get('height', 480)
            webcam_width = WEBCAM.get('width', 640)
            
            # Robot video resolution
            robot_res = ROBOT_VIDEO.get('default_resolution', '360p')
            robot_dims = {'360p': (360, 640), '540p': (540, 960), '720p': (720, 1280)}
            robot_height, robot_width = robot_dims.get(robot_res, (360, 640))
            
            features = {
                "observation.images.top": {
                    "dtype": "video",
                    "shape": [webcam_height, webcam_width, 3],
                    "names": ["height", "width", "channels"]
                },
                "observation.images.robot": {
                    "dtype": "video",
                    "shape": [robot_height, robot_width, 3],
                    "names": ["height", "width", "channels"]
                },
                "action": {
                    "dtype": "float32",
                    "shape": [9],
                    "names": ACTION_NAMES
                },
            }
            
            # Create or load dataset
            dataset_path = dataset_root / dataset_name
            if dataset_path.exists():
                # Load existing dataset to append
                self._dataset = LeRobotDataset(
                    repo_id=dataset_name,
                    root=dataset_root,
                )
            else:
                # Create new dataset
                self._dataset = LeRobotDataset.create(
                    repo_id=dataset_name,
                    root=dataset_root,
                    fps=self.fps,
                    features=features,
                )
            
            print(f"📁 Dataset: {dataset_path}")
            
        except ImportError:
            print("⚠️  lerobot not installed. Install with: pip install lerobot")
            self._dataset = None
        except Exception as e:
            print(f"⚠️  Failed to initialize dataset: {e}")
            self._dataset = None
    
    def _recording_loop(self):
        """Background recording loop - runs at configured FPS."""
        while not self._stop_event.is_set():
            current_time = time.time()
            elapsed_since_last = current_time - self._last_frame_time
            
            if elapsed_since_last >= self.frame_interval:
                self._process_frame(current_time)
                self._last_frame_time = current_time
            
            # Sleep for remaining time
            sleep_time = self.frame_interval - (time.time() - self._last_frame_time)
            if sleep_time > 0:
                self._stop_event.wait(sleep_time)
    
    def _process_frame(self, current_time: float):
        """Process a single frame at the given time."""
        self._frame_count += 1
        frame_time = current_time - self._start_time
        
        # Get frames with time offsets
        robot_frame = self.buffer.get_frame_at_time(current_time, 'robot', self._robot_offset)
        webcam_frame = self.buffer.get_frame_at_time(current_time, 'webcam', self._webcam_offset)
        
        # Aggregate commands since last frame
        start_time = self._last_frame_time if self._frame_count > 1 else self._start_time
        raw_actions = self.buffer.aggregate_commands(start_time, current_time)
        
        if self.dry_run:
            self._print_dry_run_frame(frame_time, robot_frame, webcam_frame, raw_actions)
        else:
            self._add_frame_to_dataset(robot_frame, webcam_frame, raw_actions)
    
    def _print_dry_run_frame(self, frame_time: float, robot_frame, webcam_frame, raw_actions: dict):
        """Print frame info for dry run mode (every 10th frame)."""
        # Only print every 10th frame to reduce output
        if self._frame_count % 10 != 0:
            return
        
        robot_status = "✓" if robot_frame is not None else "✗"
        webcam_status = "✓" if webcam_frame is not None else "✗"
        
        # Format action values
        move_x = raw_actions.get('move_x', 0)
        move_y = raw_actions.get('move_y', 0)
        rot = raw_actions.get('rotate_z', 0)
        grip_o = int(raw_actions.get('gripper_open', 0))
        grip_c = int(raw_actions.get('gripper_close', 0))
        arm_r = "✓" if raw_actions.get('arm_recenter', 0) else "✗"
        
        print(f"[Frame {self._frame_count:03d}] t={frame_time:.3f}s | "
              f"robot:{robot_status} webcam:{webcam_status} | "
              f"move_x={move_x:+.2f} move_y={move_y:+.2f} rot={rot:+.1f} "
              f"grip_o={grip_o} grip_c={grip_c} arm:{arm_r}")
    
    def _add_frame_to_dataset(self, robot_frame, webcam_frame, raw_actions: dict):
        """Add frame data to LeRobot dataset."""
        if self._dataset is None:
            return
        
        try:
            import torch
            
            # Normalize actions
            normalized = normalize_action(raw_actions)
            action_tensor = torch.tensor(normalized, dtype=torch.float32)
            
            # Prepare frame data
            frame_data = {
                "action": action_tensor
            }
            
            # Add images (use black frame if missing)
            if robot_frame is not None:
                frame_data["observation.images.robot"] = robot_frame
            else:
                # Create black frame
                robot_res = ROBOT_VIDEO.get('default_resolution', '360p')
                robot_dims = {'360p': (360, 640), '540p': (540, 960), '720p': (720, 1280)}
                h, w = robot_dims.get(robot_res, (360, 640))
                frame_data["observation.images.robot"] = np.zeros((h, w, 3), dtype=np.uint8)
            
            if webcam_frame is not None:
                frame_data["observation.images.top"] = webcam_frame
            else:
                # Create black frame
                h = WEBCAM.get('height', 480)
                w = WEBCAM.get('width', 640)
                frame_data["observation.images.top"] = np.zeros((h, w, 3), dtype=np.uint8)
            
            self._dataset.add_frame(frame_data)
            
        except Exception as e:
            print(f"⚠️  Failed to add frame: {e}")
    
    def _save_episode(self) -> bool:
        """Save the current episode."""
        if self._dataset is None:
            return False
        
        try:
            self._dataset.save_episode(task=self.task)
            self._dataset.consolidate()
            
            dataset_root = Path(LEROBOT.get('dataset_root', './records')).expanduser()
            dataset_name = LEROBOT.get('dataset_name', 'robomaster_teleop')
            
            print(f"\n💾 Episode saved: {self._frame_count} frames")
            print(f"   Dataset: {dataset_root / dataset_name}")
            print(f"   Task: {self.task}")
            
            return True
            
        except Exception as e:
            print(f"⚠️  Failed to save episode: {e}")
            return False
