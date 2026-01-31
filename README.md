# RoboMaster Playground

A playground for DJI RoboMaster robot experimentation, including simulation and track control capabilities. This project provides tools for controlling RoboMaster robots, simulating movement tracks, and experimenting with mecanum wheel kinematics.

## Features

- **Robot Control**: Connect to and control DJI RoboMaster robots via WiFi
- **Track Simulation**: Visualize robot movement patterns using pygame
- **Movement Tracks**: Pre-defined movement patterns (circles, boxes, zigzags, etc.)
- **Video Capture**: Stream and process video from the robot camera
- **Custom Vector Math**: Lightweight vector operations for robotics calculations

## Prerequisites

- **Python 3.8+** (tested with 3.8, 3.9, 3.10, 3.11, 3.12)
- DJI RoboMaster EP/S1 robot (for physical robot control)
- WiFi connection to the robot (for physical robot control)
- FFmpeg development libraries (for video decoding)

## Installation

This project uses a [forked RoboMaster SDK](https://github.com/tiry/RoboMaster-SDK) that has been updated for modern FFmpeg (5.x+) and Python (3.8+) compatibility.

### Prerequisites

System dependencies needed for building `libmedia_codec`:

```bash
# Ubuntu/Debian
sudo apt-get install cmake libopus-dev libavcodec-dev libavformat-dev libswscale-dev python3-dev

# Arch Linux
sudo pacman -S cmake opus ffmpeg python

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

# Install this project
pip install -e .
```

### Quick Install (Simulation Only)

If you only need the simulation mode (no physical robot):

```bash
git clone https://github.com/tiry/RoboMaster-Playground.git
cd RoboMaster-Playground
pip install pygame numpy opencv-python
python basic_simu/simulate_track.py
```

## Usage

### Simulation Mode (No Robot Required)

Run the track simulation to visualize robot movement patterns:

```bash
python basic_simu/simulate_track.py
```

**Controls:**
- **Up Arrow**: Previous track
- **Down Arrow**: Next track
- **Left/Right Arrow**: Replay current track

Available tracks:
- CircleAround
- DrawBox
- SimRBox
- Simple360
- ZigZag
- CrossLines
- TestVelocity
- Calibrate

### Robot Control (Requires RoboMaster Robot)

1. **Connect your RoboMaster robot** to your computer via WiFi (station mode)

2. **Run a track on the robot:**
   ```bash
   python run_track.py
   ```

3. **Test connection and video feed:**
   ```bash
   python test_connection.py
   ```
   This will connect to the robot, display version/battery info, and show the live video feed. Press 'q' or ESC to quit.

### Video Capture (Robot Camera)

Capture live video from the robot's camera:

```bash
python video-cap.py
```

Press any key to exit.

## Project Structure

```
RoboMaster-Playground/
├── pyproject.toml       # Project configuration and dependencies
├── README.md            # This file
├── vector.py            # Custom Vector class for math operations
├── robotrack.py         # Track definitions (movement patterns)
├── mecanum.py           # Mecanum wheel kinematics
├── run_track.py         # Execute tracks on physical robot
├── connect.py           # Basic robot connection and control
├── video-cap.py         # Robot video capture
├── test_connection.py   # Connection and video test
├── test_*.py            # Other test files
└── basic_simu/          # Simulation code (no robot required)
    ├── simulate_track.py    # Pygame-based track simulation
    ├── sim_chassis.py       # Simulated chassis for visualization
    ├── anim.py              # Animation utilities
    └── img/                 # Images for simulation
        └── Robo-Top-mini.png
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `robomaster` | DJI RoboMaster SDK for robot control |
| `opencv-python` | Computer vision and video processing |
| `numpy` | Numerical computations |
| `pygame` | Graphics and simulation display |

## Creating Custom Tracks

You can create your own movement tracks by subclassing `RoboTrack`:

```python
from robotrack import RoboTrack

class MyCustomTrack(RoboTrack):
    def genMoves(self):
        # addMove(x, y, z, speed_xy, speed_z)
        # x, y = distance in meters
        # z = rotation in degrees
        self.addMove(1, 0, 0, 1)   # Move forward 1m
        self.addMove(0, 0, 90)     # Rotate 90 degrees
        self.addMove(0, 1, 0, 1)   # Move left 1m
```

## Troubleshooting

### Connection Issues
- Ensure your RoboMaster is in station mode (WiFi router mode)
- Check that your computer is connected to the robot's WiFi network
- The robot's IP is typically `192.168.2.1`

### Display Issues in Simulation
- Make sure pygame is properly installed
- On headless systems, you may need to install additional display libraries

### RoboMaster SDK Issues
This project uses a [forked SDK](https://github.com/tiry/RoboMaster-SDK) that fixes compatibility with modern systems:
- Updated FFmpeg API calls for FFmpeg 5.x/6.x/7.x/8.x
- Updated pybind11 to v2.11 for Python 3.10+ support
- Updated cmake requirements

If you encounter build issues, ensure you have the FFmpeg development libraries installed (see Prerequisites).

## License

MIT License

## Contributing

Contributions are welcome! Feel free to submit issues and pull requests.
