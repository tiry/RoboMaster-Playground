"""
Configuration for joystick mapping and movement parameters.

Run 'robomaster control-config' to identify your controller's mappings.
"""

# =============================================================================
# CONTROLLER PRESETS
# Uncomment the preset matching your controller, or create your own
# =============================================================================

# --- Xbox Series S|X Controller ---
JOYSTICK_AXES = {
    'left_x': 0,      # Left stick X: strafe left/right
    'left_y': 1,      # Left stick Y: forward/backward
    'right_x': 3,     # Right stick X: rotate left/right
    'right_y': 4,     # Right stick Y: arm/gimbal up/down
    'left_trigger': 2,
    'right_trigger': 5,
}

JOYSTICK_BUTTONS = {
    'a': 0,           # A button (action)
    'b': 1,           # B button (cancel)
    'x': 2,           # X button
    'y': 3,           # Y button
    'lb': 4,          # Left bumper
    'rb': 5,          # Right bumper
    'back': 6,        # Back/View button
    'start': 7,       # Start/Menu button
    'guide': 8,       # Xbox button
    'left_stick': 9,  # Left stick click
    'right_stick': 10,# Right stick click
}

# --- Xbox Controller (uncomment to use) ---
# JOYSTICK_AXES = {
#     'left_x': 0,
#     'left_y': 1,
#     'right_x': 3,     # Note: Xbox often uses 3 for right X
#     'right_y': 4,     # And 4 for right Y
#     'left_trigger': 2,
#     'right_trigger': 5,
# }
#
# JOYSTICK_BUTTONS = {
#     'a': 0,
#     'b': 1,
#     'x': 2,
#     'y': 3,
#     'lb': 4,
#     'rb': 5,
#     'back': 6,
#     'start': 7,
#     'guide': 8,
#     'left_stick': 9,
#     'right_stick': 10,
# }

# Deadzone - ignore small stick movements
DEADZONE = 0.15

# SDK Chassis Mode - stick_overlay (fusion mode)
# Controls how SDK commands combine with physical controller input:
#   0 = SDK only (default) - SDK commands control robot, physical controller disabled
#   1 = Overlay (body) - SDK + physical controller, speed relative to robot body
#   2 = Overlay (gimbal) - SDK + physical controller, speed relative to gimbal direction
STICK_OVERLAY_MODE = 0

# Movement configuration
MOVEMENT = {
    # Step sizes (for discrete moves)
    'step_forward': 0.2,     # meters per step
    'step_strafe': 0.2,      # meters per step
    'step_rotate': 10,       # degrees per step
    
    # Speeds
    'speed_xy': 0.5,         # m/s for forward/strafe
    'speed_z': 60,           # deg/s for rotation
    
    # Move interval
    'move_interval': 0.1,    # seconds between move commands
    
    # For continuous mode (drive_speed API)
    'continuous_speed_xy': 0.6,  # m/s max speed in continuous mode
    'continuous_speed_z': 90,    # deg/s max rotation speed
    
    # Speed boost (A button)
    'boost_multiplier': 2.0,    # Multiplier when A is pressed
}

# Robotic Arm configuration (EP Engineering robot)
ARM = {
    'step_x': 10,            # mm per step (arm extension)
    'step_y': 10,            # mm per step (camera up/down)
}

# Telemetry configuration (--telemetry flag)
TELEMETRY = {
    'frequency': 5,          # Hz - subscription update frequency (lower is more stable)
    'window_width': 420,     # Telemetry window width
    'window_height': 420,    # Telemetry window height
}

# Robot camera configuration
ROBOT_VIDEO = {
    'default_resolution': '720p',  # Default resolution: '360p', '540p', or '720p'
}

# Webcam configuration (--static flag for external USB webcam)
# Use 'v4l2-ctl --list-devices' or 'ls /dev/video*' to find device index
WEBCAM = {
    'device_index': 0,       # USB device index (0 = /dev/video0, 1 = /dev/video1, etc.)
#    'width': 1920,            # Frame width
#    'height': 1080,           # Frame height
    'width': 1280,            # Frame width
    'height': 720,           # Frame height
    'fps': 30,               # Target frame rate
}


def apply_deadzone(value, deadzone=DEADZONE):
    """Apply deadzone to joystick value (-1 to 1)."""
    if abs(value) < deadzone:
        return 0.0
    # Scale remaining range
    sign = 1 if value > 0 else -1
    return sign * (abs(value) - deadzone) / (1 - deadzone)
