"""
input_detection.py
Author: Ellie V.

Input event detection for the XSerialOne framework.

Provides reusable primitives for detecting button presses, releases, combos,
double-taps, and other input events. Used with generators and modifiers
to add interactive input handling without complex state machines.
"""

import time
from typing import List, Optional

from XSerialOne.base import FrameState
from XSerialOne.frame_constants import Axis, Button


class InputDetector:
    """
    Detects input events from frame states.
    
    Tracks button state changes and provides methods to detect:
    - Button press (rising edge)
    - Button release (falling edge)
    - Button held (for duration)
    - Combo (multiple buttons pressed)
    - Double-tap (button pressed twice quickly)
    """
    
    def __init__(self):
        self.last_frame: Optional[FrameState] = None
        self.current_frame: Optional[FrameState] = None
        
        # Track button timing for double-tap detection
        self.button_press_times = [0.0] * 10
        self.button_tap_count = [0] * 10
        self.last_update_time = time.time()
        
        # Axis thresholds for trigger detection
        self.stick_threshold = 0.5
        self.trigger_threshold = 0.2
    
    def update(self, frame: FrameState):
        """Update detector with new frame state."""
        self.last_frame = self.current_frame
        self.current_frame = frame
        self.last_update_time = time.time()
    
    def is_pressed(self, button: Button) -> bool:
        """Check if button is currently pressed."""
        if self.current_frame is None:
            return False
        return self.current_frame.buttons[button.value]
    
    def on_press(self, button: Button) -> bool:
        """Detect rising edge (button pressed this frame)."""
        if self.current_frame is None or self.last_frame is None:
            return False
        
        is_pressed_now = self.current_frame.buttons[button.value]
        was_pressed_before = self.last_frame.buttons[button.value]
        
        return is_pressed_now and not was_pressed_before
    
    def on_release(self, button: Button) -> bool:
        """Detect falling edge (button released this frame)."""
        if self.current_frame is None or self.last_frame is None:
            return False
        
        is_pressed_now = self.current_frame.buttons[button.value]
        was_pressed_before = self.last_frame.buttons[button.value]
        
        return not is_pressed_now and was_pressed_before
    
    def on_held(self, button: Button, duration_ms: float) -> bool:
        """Detect button held for specified duration."""
        if self.current_frame is None:
            return False
        
        if not self.is_pressed(button):
            self.button_press_times[button.value] = 0.0
            return False
        
        if self.on_press(button):
            self.button_press_times[button.value] = time.time()
            return False
        
        press_time = self.button_press_times[button.value]
        if press_time == 0.0:
            return False
        
        elapsed = (time.time() - press_time) * 1000.0
        return elapsed >= duration_ms
    
    def on_combo(self, buttons: List[Button], time_window_ms: float = 100) -> bool:
        """
        Detect combo: all buttons pressed within time window.
        
        Args:
            buttons: List of buttons that must be pressed together
            time_window_ms: Time window for button presses (not implemented in basic version)
        """
        if self.current_frame is None:
            return False
        
        return all(self.is_pressed(b) for b in buttons)
    
    def on_double_tap(self, button: Button, time_window_ms: float = 300) -> bool:
        """
        Detect double-tap: button pressed twice within time window.
        
        Args:
            button: Button to detect double-tap on
            time_window_ms: Time window for second tap
        """
        if not self.on_press(button):
            return False
        
        now = time.time()
        button_idx = button.value
        
        # Check if we have a recent tap
        time_since_last_tap = (now - self.button_press_times[button_idx]) * 1000.0
        
        if self.button_tap_count[button_idx] == 0:
            # First tap
            self.button_press_times[button_idx] = now
            self.button_tap_count[button_idx] = 1
            return False
        elif time_since_last_tap < time_window_ms:
            # Second tap within window
            self.button_tap_count[button_idx] = 0
            self.button_press_times[button_idx] = 0.0
            return True
        else:
            # Too slow, reset
            self.button_press_times[button_idx] = now
            self.button_tap_count[button_idx] = 1
            return False
    
    def on_stick_move(self, axis_pair: tuple, threshold: float = None) -> bool:
        """
        Detect stick moved beyond threshold.
        
        Args:
            axis_pair: (axis_x, axis_y) tuple like (Axis.LEFTSTICKX, Axis.LEFTSTICKY)
            threshold: Movement magnitude threshold (default: stick_threshold)
        """
        if self.current_frame is None or self.last_frame is None:
            return False
        
        if threshold is None:
            threshold = self.stick_threshold
        
        axis_x, axis_y = axis_pair
        
        current_x = self.current_frame.axes[axis_x.value]
        current_y = self.current_frame.axes[axis_y.value]
        last_x = self.last_frame.axes[axis_x.value]
        last_y = self.last_frame.axes[axis_y.value]
        
        # Calculate magnitude
        import math
        current_mag = math.sqrt(current_x**2 + current_y**2)
        last_mag = math.sqrt(last_x**2 + last_y**2)
        
        # Detect if we crossed the threshold
        return (last_mag < threshold) and (current_mag >= threshold)
    
    def get_trigger_value(self, trigger: Axis) -> float:
        """Get current trigger value (-1 to 1)."""
        if self.current_frame is None:
            return 0.0
        return self.current_frame.axes[trigger.value]
    
    def on_trigger_pulled(self, trigger: Axis, threshold: float = None) -> bool:
        """Detect trigger pulled past threshold."""
        if self.current_frame is None or self.last_frame is None:
            return False
        
        if threshold is None:
            threshold = self.trigger_threshold
        
        current = self.current_frame.axes[trigger.value]
        last = self.last_frame.axes[trigger.value]
        
        return (last < threshold) and (current >= threshold)
    
    def on_dpad(self, direction: tuple) -> bool:
        """
        Detect D-pad pressed in a specific direction (rising edge).
        
        Args:
            direction: Dpad direction tuple like Dpad.UP, Dpad.LEFT, etc.
        
        Returns:
            True if D-pad just transitioned TO that direction (not while held)
        """
        if self.current_frame is None or self.last_frame is None:
            return False
        
        is_now = self.current_frame.dpad == direction
        was_before = self.last_frame.dpad == direction
        
        return is_now and not was_before
