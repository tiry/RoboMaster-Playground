"""
Joystick/controller management module.

Handles initialization, configuration, and state reading for USB game controllers.
"""

import pygame
from .config import JOYSTICK_AXES, JOYSTICK_BUTTONS, apply_deadzone


class JoystickState:
    """Immutable snapshot of joystick state."""
    
    def __init__(self, left_x=0, left_y=0, right_x=0, right_y=0,
                 left_trigger=0, right_trigger=0,
                 lb=False, rb=False, a=False, b=False, x=False, y=False):
        self.left_x = left_x          # Strafe
        self.left_y = left_y          # Forward (inverted)
        self.right_x = right_x        # Rotate
        self.right_y = right_y        # Arm Y (inverted)
        self.left_trigger = left_trigger   # Arm retract (0-1)
        self.right_trigger = right_trigger # Arm extend (0-1)
        self.lb = lb                  # Left bumper (gripper close)
        self.rb = rb                  # Right bumper (gripper open)
        self.a = a                    # A button (speed boost)
        self.b = b                    # B button
        self.x = x                    # X button
        self.y = y                    # Y button
    
    def to_dict(self):
        """Convert to dictionary for backward compatibility."""
        return {
            'left_x': self.left_x,
            'left_y': self.left_y,
            'right_x': self.right_x,
            'right_y': self.right_y,
            'left_trigger': self.left_trigger,
            'right_trigger': self.right_trigger,
            'lb': self.lb,
            'rb': self.rb,
            'a': self.a,
            'b': self.b,
            'x': self.x,
            'y': self.y,
        }


class Joystick:
    """Manages a USB game controller."""
    
    def __init__(self, index=0):
        """Initialize joystick at given index.
        
        Args:
            index: Joystick index (default 0 for first controller)
        
        Raises:
            RuntimeError: If no joystick is detected
        """
        pygame.init()
        pygame.joystick.init()
        
        if pygame.joystick.get_count() == 0:
            raise RuntimeError("No joystick detected! Please connect a controller.")
        
        if index >= pygame.joystick.get_count():
            raise RuntimeError(f"Joystick index {index} not found. Only {pygame.joystick.get_count()} controller(s) available.")
        
        self._joystick = pygame.joystick.Joystick(index)
        self._joystick.init()
    
    @property
    def name(self):
        """Get joystick name."""
        return self._joystick.get_name()
    
    @property
    def num_axes(self):
        """Get number of axes."""
        return self._joystick.get_numaxes()
    
    @property
    def num_buttons(self):
        """Get number of buttons."""
        return self._joystick.get_numbuttons()
    
    def get_state(self) -> JoystickState:
        """Read current joystick state with deadzone applied.
        
        Returns:
            JoystickState: Current state of all inputs
        """
        pygame.event.pump()  # Process events
        
        # Get axis values with deadzone
        left_x = apply_deadzone(self._joystick.get_axis(JOYSTICK_AXES['left_x']))
        left_y = apply_deadzone(self._joystick.get_axis(JOYSTICK_AXES['left_y']))
        right_x = apply_deadzone(self._joystick.get_axis(JOYSTICK_AXES['right_x']))
        right_y = apply_deadzone(self._joystick.get_axis(JOYSTICK_AXES['right_y']))
        
        # Triggers (normalize from -1..1 to 0..1)
        left_trigger = (self._joystick.get_axis(JOYSTICK_AXES['left_trigger']) + 1) / 2
        right_trigger = (self._joystick.get_axis(JOYSTICK_AXES['right_trigger']) + 1) / 2
        
        # Buttons
        lb = bool(self._joystick.get_button(JOYSTICK_BUTTONS['lb']))
        rb = bool(self._joystick.get_button(JOYSTICK_BUTTONS['rb']))
        a = bool(self._joystick.get_button(JOYSTICK_BUTTONS['a']))
        b = bool(self._joystick.get_button(JOYSTICK_BUTTONS.get('b', 1)))
        x = bool(self._joystick.get_button(JOYSTICK_BUTTONS.get('x', 2)))
        y = bool(self._joystick.get_button(JOYSTICK_BUTTONS.get('y', 3)))
        
        return JoystickState(
            left_x=left_x,
            left_y=-left_y,          # Invert Y
            right_x=right_x,
            right_y=-right_y,        # Invert Y
            left_trigger=left_trigger,
            right_trigger=right_trigger,
            lb=lb,
            rb=rb,
            a=a,
            b=b,
            x=x,
            y=y,
        )
    
    def close(self):
        """Clean up pygame resources."""
        try:
            pygame.quit()
        except:
            pass


def init_joystick(index=0) -> Joystick:
    """Initialize and return a Joystick instance.
    
    Args:
        index: Joystick index (default 0)
    
    Returns:
        Joystick: Initialized joystick
    
    Raises:
        RuntimeError: If no joystick is detected
    """
    return Joystick(index)
