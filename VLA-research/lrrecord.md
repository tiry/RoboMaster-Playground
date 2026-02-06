# LeRobot Recording Specification

## Overview

Replace the existing JSON record format with LeRobot-based recording for VLA training datasets.

**Changes:**
- Keep `--record` flag but output LeRobot format instead of JSON
- Remove `--replay` flag and replay functionality
- Remove `cli/recorder.py` (old JSON recorder)
- Keep `driver/recording.py` (useful for command interception)
- Add `--dry-run` flag for testing without saving
- Add `lerobot` dependency

## Recording Flow

### CLI Usage

```bash
# Start recording (recording starts immediately)
robomaster drive --record

# With custom episode description
robomaster drive --record --task "Pick up the red cube"

# With custom FPS
robomaster drive --record --fps 15

# Dry run mode (prints one line per frame, no saving)
robomaster drive --record --dry-run

# Full options
robomaster drive --record --task "Patrol route A" --fps 30 -d 2 --dry-run
```

### Controls During Recording
- **Back button**: Save episode and stop recording
- **q/ESC**: Abort recording without saving
- All other controls work normally (drive, arm, gripper)

## Configuration (cli/config.py)

```python
# LeRobot recording configuration
LEROBOT = {
    # Dataset settings
    'dataset_root': './records',              # Local storage path
    'dataset_name': 'robomaster_teleop',      # Dataset name
    'default_fps': 30,                        # Recording FPS
    'default_task': 'do something with Robomaster',  # Default episode description
    
    # Buffer settings
    'buffer_duration': 2.0,                   # Seconds of frames to buffer (max 5s)
    
    # Time offsets for camera synchronization (< 1s)
    'robot_camera_offset': 0.0,               # Seconds offset for robot camera
    'static_camera_offset': 0.0,              # Seconds offset for USB webcam
    
    # Action normalization ranges (all values map to [-1, 1])
    # Format: (min_value, max_value) - raw values outside range are clipped
    'action_ranges': {
        'move_x': (-2.0, 2.0),                # m/s range for forward/backward
        'move_y': (-2.0, 2.0),                # m/s range for strafe
        'rotate_z': (-180.0, 180.0),          # deg/s range for rotation
        'gripper_open': (0, 100),             # Power % for open gripper
        'gripper_close': (0, 100),            # Power % for close gripper
        'arm_recenter': (0, 1),               # Boolean (0 or 1)
        'arm_x': (80, 220),                   # mm range for arm X
        'arm_y': (-40, 90),                   # mm range for arm Y
    },
}
```

## Data Schema

### Features

```python
features = {
    # Observations (what AI sees)
    "observation.images.top": {
        "dtype": "video", 
        "shape": [height, width, 3],  # From WEBCAM config
        "names": ["height", "width", "channels"]
    },
    "observation.images.robot": {
        "dtype": "video", 
        "shape": [height, width, 3],  # From robot video resolution
        "names": ["height", "width", "channels"]
    },
    
    # Actions (what teleoperator did) - all normalized to [-1, 1]
    "action": {
        "dtype": "float32", 
        "shape": [9], 
        "names": [
            "move_x",         # Chassis velocity forward/back (m/s) → normalized
            "move_y",         # Chassis velocity strafe (m/s) → normalized
            "rotate_z",       # Chassis rotation (deg/s) → normalized
            "gripper_open",   # Gripper open power (0-100%) → normalized
            "gripper_close",  # Gripper close power (0-100%) → normalized
            "arm_recenter",   # Arm recenter (0 or 1) → normalized
            "arm_x",          # Arm X position (mm) → normalized
            "arm_y",          # Arm Y position (mm) → normalized
            "unused"          # Padding, always 0.0
        ]
    },
}
```

### Action Normalization

All actions normalized to [-1, 1] using configurable ranges from `LEROBOT['action_ranges']`.

**Normalization formula:**
```
normalized = (value - min) / (max - min) * 2 - 1
```

**Denormalization formula:**
```
value = (normalized + 1) / 2 * (max - min) + min
```

| Action | Raw Type | Raw Range (default) | Normalized Range |
|--------|----------|---------------------|------------------|
| `move_x` | float | -2.0 to 2.0 m/s | [-1, 1] |
| `move_y` | float | -2.0 to 2.0 m/s | [-1, 1] |
| `rotate_z` | float | -180 to 180 deg/s | [-1, 1] |
| `gripper_open` | int | 0 to 100 (power %) | [-1, 1] |
| `gripper_close` | int | 0 to 100 (power %) | [-1, 1] |
| `arm_recenter` | bool | 0 or 1 | [-1, 1] |
| `arm_x` | float | 80 to 220 mm | [-1, 1] |
| `arm_y` | float | -40 to 90 mm | [-1, 1] |

### Normalization Functions

```python
# In cli/lerobot_recorder.py

def normalize_action(raw_actions: dict, action_ranges: dict) -> list:
    """Convert raw action values to normalized [-1, 1] tensor.
    
    Args:
        raw_actions: Dict with raw values {'move_x': 0.5, 'gripper_open': 50, ...}
        action_ranges: Dict of (min, max) tuples from config
        
    Returns:
        List of 9 normalized float32 values
    """
    action_names = ['move_x', 'move_y', 'rotate_z', 'gripper_open', 
                    'gripper_close', 'arm_recenter', 'arm_x', 'arm_y', 'unused']
    
    normalized = []
    for name in action_names:
        if name == 'unused':
            normalized.append(0.0)
            continue
            
        raw_value = raw_actions.get(name, 0.0)
        min_val, max_val = action_ranges.get(name, (0, 1))
        
        # Clip to range and normalize to [-1, 1]
        clipped = max(min_val, min(max_val, raw_value))
        norm = (clipped - min_val) / (max_val - min_val) * 2 - 1
        normalized.append(float(norm))
    
    return normalized


def denormalize_action(normalized_actions: list, action_ranges: dict) -> dict:
    """Convert normalized [-1, 1] tensor back to raw action values.
    
    Args:
        normalized_actions: List of 9 normalized values
        action_ranges: Dict of (min, max) tuples from config
        
    Returns:
        Dict with raw values {'move_x': 0.5, 'gripper_open': 50, ...}
    """
    action_names = ['move_x', 'move_y', 'rotate_z', 'gripper_open', 
                    'gripper_close', 'arm_recenter', 'arm_x', 'arm_y', 'unused']
    
    raw_actions = {}
    for i, name in enumerate(action_names):
        if name == 'unused':
            continue
            
        norm_value = normalized_actions[i]
        min_val, max_val = action_ranges.get(name, (0, 1))
        
        # Denormalize from [-1, 1] to raw range
        raw = (norm_value + 1) / 2 * (max_val - min_val) + min_val
        raw_actions[name] = raw
    
    return raw_actions
```

## Architecture

### Recording Thread

A dedicated recording thread runs at configured FPS (e.g., 30 Hz):

```
Main Thread                    Recording Thread
    │                               │
    ├─ drive_loop()                 │
    │   ├─ read joystick            │
    │   ├─ send commands ──────────►│ (append to command buffer)
    │   ├─ get robot frame ────────►│ (append to frame buffer)
    │   ├─ get webcam frame ───────►│ (append to frame buffer)
    │   └─ display video            │
    │                               │
    │                               ├─ every 1/30s:
    │                               │   ├─ pick best robot frame (with offset)
    │                               │   ├─ pick best webcam frame (with offset)
    │                               │   ├─ aggregate commands since last frame
    │                               │   └─ dataset.add_frame()
    │                               │
    ├─ Back button pressed          │
    │   └─ signal stop ────────────►│ save_episode()
    │                               │
    └─ cleanup                      └─ dataset.save()
```

### Buffer Structure

```python
class FrameBuffer:
    """Thread-safe ring buffer for frames and commands."""
    
    def __init__(self, max_duration: float = 2.0, fps: int = 30):
        self.max_frames = int(max_duration * fps)
        
        # Frame buffers (timestamp, frame)
        self.robot_frames = deque(maxlen=self.max_frames)
        self.webcam_frames = deque(maxlen=self.max_frames)
        
        # Command buffer (timestamp, command_dict)
        self.commands = deque(maxlen=self.max_frames * 10)  # More commands than frames
        
        self._lock = threading.Lock()
    
    def add_robot_frame(self, frame, timestamp):
        with self._lock:
            self.robot_frames.append((timestamp, frame))
    
    def add_webcam_frame(self, frame, timestamp):
        with self._lock:
            self.webcam_frames.append((timestamp, frame))
    
    def add_command(self, command: dict, timestamp):
        """Add command like {'move_x': 0.5, 'gripper_open': True}"""
        with self._lock:
            self.commands.append((timestamp, command))
    
    def get_frame_at_time(self, target_time: float, source: str, offset: float = 0.0):
        """Get frame closest to target_time + offset."""
        pass
    
    def aggregate_commands(self, start_time: float, end_time: float) -> dict:
        """Aggregate all commands between start and end time.
        
        - Numeric values (move_x, move_y, rotate_z, gripper_open, gripper_close, arm_x, arm_y): SUM
        - Boolean values (arm_recenter): OR (1.0 if any True)
        """
        pass
```

### Command Aggregation

Between frames, multiple commands may be sent. Aggregation rules:

**Numeric commands (SUM):**
All velocity, gripper power %, and arm position commands are summed:

```
t=0.00: move_x=0.5
t=0.01: move_x=0.3, move_y=0.2
t=0.02: rotate_z=45, gripper_open=50
t=0.03: gripper_open=30
─────────────────────────────
Frame at t=0.033:
  move_x = 0.5 + 0.3 = 0.8
  move_y = 0.0 + 0.2 = 0.2
  rotate_z = 0.0 + 45 = 45
  gripper_open = 50 + 30 = 80  (capped at 100)
```

**Boolean commands (OR):**
Only `arm_recenter` is boolean (0 or 1). If any command was 1, result is 1:

```
t=0.00: arm_recenter=0
t=0.01: arm_recenter=1
t=0.02: arm_recenter=0
─────────────────────────────
Frame at t=0.033:
  arm_recenter = 0 OR 1 OR 0 = 1
```

## Dry Run Mode

When `--dry-run` is used with `--record`, prints one line per frame instead of saving:

```
[Frame 001] t=0.033s | robot:✓ webcam:✓ | move_x=+0.50 move_y=+0.00 rot=+0.00 grip_o=0 grip_c=0 arm:✗
[Frame 002] t=0.066s | robot:✓ webcam:✓ | move_x=+0.50 move_y=+0.10 rot=+0.00 grip_o=0 grip_c=0 arm:✗
[Frame 003] t=0.100s | robot:✓ webcam:✓ | move_x=+0.30 move_y=+0.10 rot=+45.0 grip_o=50 grip_c=0 arm:✗
...
```

Shows:
- Frame number and timestamp
- Camera status (✓ = frame captured, ✗ = missing)
- Aggregated raw action values (before normalization)

## Files to Modify/Create

### New Files
- `cli/lerobot_recorder.py` - LeRobot recording logic, FrameBuffer, RecordingThread, normalize/denormalize functions

### Modify
- `cli/drive.py` - Update `--record` to use LeRobot; add `--task`, `--fps`, `--dry-run` flags; remove `--replay`
- `cli/config.py` - Add LEROBOT configuration section
- `driver/recording.py` - Keep for command interception (may need updates for new format)
- `pyproject.toml` - Add `lerobot` dependency
- `README.md` - Update documentation

### Delete
- `cli/recorder.py` - Old JSON recorder (replaced by lerobot_recorder.py)

## Dependencies

Add to `pyproject.toml`:

```toml
dependencies = [
    ...
    "lerobot>=0.1.0",
]
```

## Implementation Checklist

- [ ] Add LEROBOT config section to config.py
- [ ] Create cli/lerobot_recorder.py with FrameBuffer and RecordingThread
- [ ] Implement normalize_action() and denormalize_action() functions
- [ ] Update drive.py: modify --record to use LeRobot format
- [ ] Update drive.py: add --task, --fps, --dry-run flags
- [ ] Update drive.py: remove --replay flag and replay_loop
- [ ] Integrate recorder with drive_loop (frame/command capture to buffer)
- [ ] Implement time-offset frame selection
- [ ] Implement command aggregation (sum for numeric, OR for arm_recenter)
- [ ] Add Back button to save episode
- [ ] Implement dry-run mode (print frame info instead of saving)
- [ ] Delete cli/recorder.py
- [ ] Add lerobot to pyproject.toml
- [ ] Update README.md
