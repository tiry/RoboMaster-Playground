# Detailed Installation Guide

This guide provides step-by-step instructions for setting up the RoboMaster Playground project with all dependencies including LeRobot support for VLA training.

## Table of Contents

- [Prerequisites](#prerequisites)
- [System Dependencies](#system-dependencies)
- [Python Setup](#python-setup)
- [Forked RoboMaster SDK](#forked-robomaster-sdk)
- [Project Installation](#project-installation)
- [LeRobot Integration](#lerobot-integration)
- [Xbox Controller Setup](#xbox-controller-setup)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python 3.10 or 3.11** (required for LeRobot compatibility)
  - LeRobot requires Python 3.10+
  - Tested with Python 3.11.14
- DJI RoboMaster EP/S1 robot (for physical robot control)
- WiFi connection to the robot
- FFmpeg development libraries (for video decoding)
- USB game controller (for joystick control)

**⚠️ Important:** Python 3.12+ is NOT currently supported due to LeRobot compatibility issues.

---

## System Dependencies

### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install -y \
    cmake \
    libopus-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    python3-dev \
    python3-venv \
    libgtk2.0-dev \
    pkg-config
```

### Arch Linux

```bash
sudo pacman -S cmake opus ffmpeg python dkms linux-headers gtk2 base-devel
```

### macOS

```bash
brew install cmake opus ffmpeg python
```

### Why These Dependencies?

| Package | Purpose |
|---------|---------|
| `cmake` | Build the libmedia_codec library |
| `libopus-dev` | Audio codec for RoboMaster SDK |
| `libavcodec-dev` | FFmpeg video decoding |
| `libavformat-dev` | FFmpeg format handling |
| `libswscale-dev` | FFmpeg video scaling |
| `libgtk2.0-dev` | GUI support for OpenCV (cv2.imshow) |

---

## Python Setup

### Using pyenv (Recommended)

[pyenv](https://github.com/pyenv/pyenv) allows managing multiple Python versions:

```bash
# Install pyenv (if not installed)
curl https://pyenv.run | bash

# Add to your shell (bash)
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

# Install Python 3.11
pyenv install 3.11.14

# Use Python 3.11 for this project
cd /path/to/RoboMaster-Playground
pyenv local 3.11.14

# Verify
python --version  # Should show Python 3.11.14
```

### Using System Python

If your system has Python 3.10 or 3.11:

```bash
python3.11 -m venv venv
# or
python3.10 -m venv venv
```

---

## Forked RoboMaster SDK

This project uses a **forked RoboMaster SDK** instead of the official DJI SDK.

### Why the Fork?

1. **Modern FFmpeg compatibility** - The official SDK uses deprecated FFmpeg APIs that don't compile with FFmpeg 5.x/6.x/7.x/8.x
2. **Python 3.10+ support** - Updated pybind11 to v2.11 for modern Python compatibility
3. **Updated cmake requirements** - Works with modern toolchains

**Fork repository:** https://github.com/tiry/RoboMaster-SDK

### Installing the Forked SDK

The forked SDK requires installing two components:

#### 1. Clone the Forked SDK

```bash
git clone https://github.com/tiry/RoboMaster-SDK.git /tmp/RoboMaster-SDK
```

#### 2. Install libmedia_codec

This is a native C++ library that requires compilation:

```bash
# Make sure venv is activated
source venv/bin/activate

# Install libmedia_codec (this builds native code)
pip install /tmp/RoboMaster-SDK/lib/libmedia_codec
```

**Expected output:**
```
Building wheel for libmedia_codec (pyproject.toml) ...
-- Build files have been written to: ...
[100%] Built target media_codec
Successfully built libmedia_codec
Successfully installed libmedia_codec-0.0.3
```

#### 3. Install robomaster SDK

```bash
pip install git+https://github.com/tiry/RoboMaster-SDK.git
```

---

## Project Installation

### 1. Clone the Repository

```bash
git clone https://github.com/tiry/RoboMaster-Playground.git
cd RoboMaster-Playground
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install the Forked SDK (see above section)

```bash
git clone https://github.com/tiry/RoboMaster-SDK.git /tmp/RoboMaster-SDK
pip install /tmp/RoboMaster-SDK/lib/libmedia_codec
pip install git+https://github.com/tiry/RoboMaster-SDK.git
```

### 4. Install the Project

**Basic installation (without LeRobot):**
```bash
pip install -e .
```

**With LeRobot support (recommended):**
```bash
pip install -e ".[recording]"
```

### 5. Fix OpenCV GUI Support

LeRobot installs `opencv-python-headless` which lacks GUI support. After installing LeRobot, replace it with the full OpenCV:

```bash
pip uninstall -y opencv-python-headless
pip install "opencv-python>=4.9.0,<4.13.0"
```

**Note:** You'll see a pip warning about lerobot requiring opencv-python-headless - this can be safely ignored.

---

## LeRobot Integration

LeRobot provides tooling for robot learning, including data collection in the LeRobot format for VLA (Vision-Language-Action) training.

### Install LeRobot

LeRobot is included as an optional dependency:

```bash
pip install -e ".[recording]"
```

Or install directly:

```bash
pip install lerobot
```

### Post-Installation Fix

**Important:** After installing LeRobot, fix the OpenCV conflict:

```bash
pip uninstall -y opencv-python-headless
pip install "opencv-python>=4.9.0,<4.13.0"
```

### Verify LeRobot

```bash
python -c "import lerobot; print('LeRobot version:', lerobot.__version__)"
```

---

## Xbox Controller Setup

### Linux

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
# Log out and back in for group changes to take effect
```

### Verify Controller

```bash
# Check if controller is detected
ls /dev/input/js*

# Test with the CLI
robomaster control-config
```

---

## Verification

After installation, verify everything works:

### 1. Check CLI is Available

```bash
robomaster --help
robomaster --version
```

### 2. Check Python Packages

```bash
python -c "import robomaster; print('RoboMaster SDK:', robomaster.__version__)"
python -c "import cv2; print('OpenCV:', cv2.__version__); print('VideoCapture:', hasattr(cv2, 'VideoCapture')); print('imshow:', hasattr(cv2, 'imshow'))"
python -c "import pygame; print('Pygame:', pygame.__version__)"
python -c "import lerobot; print('LeRobot:', lerobot.__version__)"
```

**Expected output:**
```
RoboMaster SDK: 0.1.1.6x
OpenCV: 4.12.0
VideoCapture: True
imshow: True
Pygame: 2.6.1
LeRobot: 0.4.3
```

### 3. Test Simulation Mode (No Robot Required)

```bash
robomaster drive --simu
```

### 4. Test with Real Robot

Connect to your robot's WiFi network, then:

```bash
robomaster info
robomaster drive
```

---

## Troubleshooting

### OpenCV GUI Error

**Error:**
```
cv2.error: The function is not implemented. Rebuild the library with Windows, GTK+ 2.x or Cocoa support.
```

**Solution:**
```bash
pip uninstall -y opencv-python-headless
pip install "opencv-python>=4.9.0,<4.13.0"

# Make sure libgtk2.0-dev is installed (Linux)
sudo apt-get install libgtk2.0-dev pkg-config
```

### cv2 Module Missing Attributes

**Error:**
```
AttributeError: module 'cv2' has no attribute 'VideoCapture'
```

**Solution:**
```bash
pip install --force-reinstall "opencv-python>=4.9.0,<4.13.0"
```

### libmedia_codec Build Fails

**Error:** cmake or compilation errors during `pip install /tmp/RoboMaster-SDK/lib/libmedia_codec`

**Solution:**
1. Ensure cmake is installed: `cmake --version`
2. Install FFmpeg development headers:
   ```bash
   sudo apt-get install libavcodec-dev libavformat-dev libswscale-dev libopus-dev
   ```
3. Try cleaning and rebuilding:
   ```bash
   pip cache purge
   pip install /tmp/RoboMaster-SDK/lib/libmedia_codec --no-cache-dir
   ```

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

### Robot Connection Issues

- Ensure robot is in station mode (WiFi router mode)
- Connect to robot's WiFi network
- Robot IP is typically `192.168.2.1`
- Check if robot is powered on and not in sleep mode

### Python Version Issues

**Error:** `lerobot` fails to install or import

**Solution:** Use Python 3.10 or 3.11:
```bash
pyenv install 3.11.14
pyenv local 3.11.14
rm -rf venv
python -m venv venv
source venv/bin/activate
# Continue with installation...
```

---

## Quick Reference

### Complete Installation Commands

```bash
# 1. Clone project
git clone https://github.com/tiry/RoboMaster-Playground.git
cd RoboMaster-Playground

# 2. Set Python version (if using pyenv)
pyenv local 3.11.14

# 3. Create venv
python -m venv venv
source venv/bin/activate

# 4. Install forked SDK
git clone https://github.com/tiry/RoboMaster-SDK.git /tmp/RoboMaster-SDK
pip install /tmp/RoboMaster-SDK/lib/libmedia_codec
pip install git+https://github.com/tiry/RoboMaster-SDK.git

# 5. Install project with LeRobot
pip install -e ".[recording]"

# 6. Fix OpenCV
pip uninstall -y opencv-python-headless
pip install "opencv-python>=4.9.0,<4.13.0"

# 7. Verify
robomaster --version
robomaster drive --simu
```

---

## Support

If you encounter issues not covered here:

1. Check the [GitHub Issues](https://github.com/tiry/RoboMaster-Playground/issues)
2. Review the main [README.md](README.md) for usage details
3. Open a new issue with:
   - Python version (`python --version`)
   - OS and version
   - Full error traceback
   - Steps to reproduce
