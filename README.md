# RoboMaster Playground

A playground for DJI RoboMaster robot experimentation, including simulation, CLI control, and joystick support. This project provides tools for controlling RoboMaster robots, simulating movement, and experimenting with mecanum wheel kinematics.

## Features

- **CLI Interface**: Command-line tools for robot control (`robomaster` command)
- **Joystick Control**: Drive your robot with Xbox/PS5 controllers
- **Simulation Mode**: Test controls without a physical robot
- **Video Streaming**: Live video feed from robot camera
- **Robot Info**: Query battery, sensors, gimbal, arm status
- **Track Simulation**: Visualize robot movement patterns using pygame

## Prerequisites

- **Python 3.8+** (tested with 3.8, 3.9, 3.10, 3.11, 3.12)
- DJI RoboMaster EP/S1 robot (for physical robot control)
- WiFi connection to the robot (for physical robot control)
- FFmpeg development libraries (for video decoding)
- USB game controller (for joystick control)

## Installation

### System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get install cmake libopus-dev libavcodec-dev libavformat-dev libswscale-dev python3-dev

# Arch Linux
sudo pacman -S cmake opus ffmpeg python dkms linux-headers

# macOS
brew install cmake opus ffmpeg python
```

### Installation Steps

```bash
# Clone the repository
git clone https://github.com/tiry/RoboMaster-Playground.git
cd RoboMaster-Playground

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install libmedia_codec from forked SDK (required for video)
git clone https://github.com/tiry/RoboMaster-SDK.git /tmp/RoboMaster-SDK
pip install /tmp/RoboMaster-SDK/lib/libmedia_codec

# Install robomaster SDK
pip install git+https://github.com/tiry/RoboMaster-SDK.git

# Install this project (includes CLI)
pip install -e .
```

### Xbox Controller Setup (Linux)

For Xbox controller support on Linux, install the xone driver:

```bash
# Install DKMS and headers
sudo pacman -S dkms linux-headers  # Arch
# or: sudo apt install dkms linux-headers-$(uname -r)  # Debian/Ubuntu

# Install xone driver
git clone https://github.com/medusalix/xone.git /tmp/xone
cd /tmp/xone && sudo ./install.sh

# Add yourself to input group
sudo usermod -aG input $USER
# Log out and back in
```

## CLI Usage

After installation, the `robomaster` command is available:

```bash
robomaster --help              # Show all commands
robomaster --version           # Show version
```

### Available Commands

| Command | Description |
|---------|-------------|
| `robomaster info` | Get robot information (version, battery, sensors) |
| `robomaster video` | Open live video stream from robot camera |
| `robomaster drive` | Drive robot with USB joystick |
| `robomaster control-config` | Configure and test your game controller |

### Get Robot Info

```bash
robomaster info                # Basic info with 1.5s sensor collection
robomaster info -w 3           # Wait 3 seconds for more sensor data
```

Displays:
- Robot version and serial number
- Battery level
- Chassis position, attitude, velocity
- Gimbal angle (if available)
- Robotic arm position (if available)
- Gripper and servo status

### Video Streaming

```bash
robomaster video               # Open video stream (360p default)
robomaster video -res 720p     # Higher resolution
```

Press 'q' or ESC to quit.

### Joystick Control

#### 1. Configure Your Controller

First, test that your controller is detected:

```bash
robomaster control-config
```

This shows real-time axis and button values to help configure your controller.

#### 2. Drive in Simulation Mode

Test the controls without connecting to a robot:

```bash
robomaster drive --simu
```

#### 3. Drive the Real Robot

Connect to your robot's WiFi, then:

```bash
robomaster drive               # With video feed
robomaster drive --no-video    # Without video (lower latency)
robomaster drive -m step       # Discrete step mode
```

**Options:**
- `--simu`: Simulation mode (no robot connection)
- `--no-video`: Disable video feed
- `-m continuous`: Real-time speed control (default)
- `-m step`: Discrete movements
- `-res 720p`: Video resolution (360p/540p/720p)

#### Controller Mapping (Xbox)

| Control | Action |
|---------|--------|
| **Left Stick** | Move robot (forward/back/strafe) |
| **Right Stick X** | Rotate robot |
| **Right Stick Y** | Arm up/down |
| **Right Trigger** | Extend arm (X+) |
| **Left Trigger** | Retract arm (X-) |
| **RB (Right Bumper)** | Open gripper |
| **LB (Left Bumper)** | Close gripper |
| **A Button** | Speed boost (2x) |
| **q/ESC** | Quit |

**Video Overlay:**
- Shows joystick values, arm status, gripper state
- `[BOOST]` indicator when A is pressed (yellow)

### Configuration

Edit `cli/config.py` to adjust:

- **Controller mapping**: Axis/button indices for your controller
- **Deadzone**: Ignore small stick movements (default 0.15)
- **Movement speeds**: Step sizes and max speeds
- **Arm settings**: Step sizes for arm extension/height
- **Speed boost**: Multiplier when A button is pressed (default 2x)

**Example configuration:**
```python
MOVEMENT = {
    'continuous_speed_xy': 0.3,  # m/s (normal speed)
    'continuous_speed_z': 90,    # deg/s (rotation)
    'boost_multiplier': 2.0,     # 2x speed when holding A
}

ARM = {
    'step_x': 10,  # mm per step (extend/retract)
    'step_y': 10,  # mm per step (up/down)
}
```

## Legacy Usage

### Simulation Mode (No Robot Required)

Run the track simulation:

```bash
python basic_simu/simulate_track.py
```

**Controls:**
- **Up/Down Arrow**: Change track
- **Left/Right Arrow**: Replay

### Run Pre-defined Tracks

```bash
python run_track.py
```

## Project Structure

```
RoboMaster-Playground/
├── pyproject.toml           # Project config and dependencies
├── README.md                # This file
├── cli/                     # CLI commands
│   ├── __init__.py          # CLI entry point
│   ├── config.py            # Controller and movement config
│   ├── connection.py        # Robot connection context manager
│   ├── control_config.py    # Controller configuration helper
│   ├── drive.py             # Joystick drive command
│   ├── info.py              # Robot info command
│   └── video.py             # Video stream command
├── basic_simu/              # Simulation code
│   ├── simulate_track.py    # Track simulation
│   ├── sim_chassis.py       # Simulated chassis
│   └── img/                 # Robot images
└── old/                     # Legacy scripts
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `robomaster` | DJI RoboMaster SDK |
| `opencv-python` | Video processing |
| `pygame` | Joystick input and simulation display |
| `click` | CLI framework |
| `numpy` | Numerical computations |

## Troubleshooting

### Controller Not Detected

1. Check if user is in `input` group:
   ```bash
   groups $USER
   ```

2. Add to input group if needed:
   ```bash
   sudo usermod -aG input $USER
   # Log out and back in
   ```

3. Check for `/dev/input/js0`:
   ```bash
   ls -la /dev/input/js*
   ```

4. For Xbox: Install xone driver (see Installation)
5. For PS5: May need `hid-playstation` driver

### Connection Issues

- Ensure robot is in station mode (WiFi router mode)
- Connect to robot's WiFi network
- Robot IP is typically `192.168.2.1`

### Video Issues

- Install FFmpeg libraries (see Prerequisites)
- Try lower resolution: `robomaster video -res 360p`

## License

MIT License

## Contributing

Contributions welcome! Feel free to submit issues and pull requests.
