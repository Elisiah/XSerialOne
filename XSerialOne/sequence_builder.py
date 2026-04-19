"""
sequence_builder.py
Author: Ellie V.

Simple fluent API for building sequences programmatically.

This provides an easy way to create input sequences in code without
the complexity of the old MacroBuilder. It's complementary to the GUI editor
and the recording system.

COEXISTS with MacroSystem - both systems are supported.
"""

from typing import List, Tuple

from XSerialOne.base import FrameState
from XSerialOne.frame_constants import Button
from XSerialOne.sequence import Sequence, SequenceFrame


class SequenceBuilder:
    """
    Build input sequences programmatically using a simple fluent API.
    
    Example:
        seq = (SequenceBuilder("combo")
            .frame(buttons=[Button.A], duration_ms=0)      # Press A at time 0
            .frame(buttons=[], duration_ms=50)             # Release A, wait 50ms
            .frame(buttons=[Button.B], duration_ms=50)     # Press B, wait 50ms
            .frame(buttons=[], duration_ms=50)             # Release B
            .build())
        
        seq.save("combo.json")
    """
    
    def __init__(self, name: str, description: str = ""):
        """Initialize a new sequence builder."""
        self.sequence = Sequence(name=name, description=description)
        self.current_time_ms = 0.0
    
    def frame(self,
              buttons: List[Button] = None,
              stick_left: Tuple[float, float] = (0.0, 0.0),
              stick_right: Tuple[float, float] = (0.0, 0.0),
              triggers: Tuple[float, float] = (0.0, 0.0),
              duration_ms: float = 0.0) -> 'SequenceBuilder':
        """
        Add a frame to the sequence.
        
        Args:
            buttons: List of Button enums to press (e.g., [Button.A, Button.B])
            stick_left: (x, y) for left stick (-1.0 to 1.0)
            stick_right: (x, y) for right stick (-1.0 to 1.0)
            triggers: (left, right) trigger values (-1.0 to 1.0)
            duration_ms: How long to hold this frame
        
        Returns:
            self (for chaining)
        """
        # Build button state
        btn_state = [False] * 10
        if buttons:
            for b in buttons:
                btn_state[b.value] = True
        
        # Build frame
        frame = FrameState(
            buttons=tuple(btn_state),
            axes=(
                stick_left[0], stick_left[1],
                stick_right[0], stick_right[1],
                triggers[0], triggers[1]
            ),
            dpad=(0, 0)
        )
        
        # Add to sequence
        self.sequence.frames.append(SequenceFrame(
            timestamp_ms=self.current_time_ms,
            frame=frame.to_dict()
        ))
        
        self.current_time_ms += duration_ms
        return self
    
    def wait(self, duration_ms: float) -> 'SequenceBuilder':
        """
        Wait (hold neutral input) for specified duration.
        
        Args:
            duration_ms: Time to wait in milliseconds
        
        Returns:
            self (for chaining)
        """
        return self.frame(duration_ms=duration_ms)
    
    def press(self, *buttons: Button, duration_ms: float = 0) -> 'SequenceBuilder':
        """
        Press one or more buttons.
        
        Args:
            buttons: Button(s) to press
            duration_ms: How long to hold (0 = just this frame)
        
        Returns:
            self (for chaining)
        """
        return self.frame(buttons=list(buttons), duration_ms=duration_ms)
    
    def release(self, *buttons: Button, duration_ms: float = 0) -> 'SequenceBuilder':
        """Release buttons (hold neutral)."""
        return self.wait(duration_ms)
    
    def stick(self, 
              which: str = "left",
              x: float = 0.0, 
              y: float = 0.0,
              duration_ms: float = 0) -> 'SequenceBuilder':
        """
        Move a stick.
        
        Args:
            which: "left" or "right"
            x: X position (-1.0 to 1.0)
            y: Y position (-1.0 to 1.0)
            duration_ms: How long to hold
        
        Returns:
            self (for chaining)
        """
        if which.lower() == "left":
            return self.frame(stick_left=(x, y), duration_ms=duration_ms)
        elif which.lower() == "right":
            return self.frame(stick_right=(x, y), duration_ms=duration_ms)
        else:
            raise ValueError("which must be 'left' or 'right'")
    
    def trigger(self,
                which: str = "right",
                value: float = 1.0,
                duration_ms: float = 0) -> 'SequenceBuilder':
        """
        Pull a trigger.
        
        Args:
            which: "left" or "right"
            value: Trigger value (-1.0 to 1.0, typically 0-1 for normal use)
            duration_ms: How long to hold
        
        Returns:
            self (for chaining)
        """
        triggers = (0.0, 0.0)
        if which.lower() == "left":
            triggers = (value, 0.0)
        elif which.lower() == "right":
            triggers = (0.0, value)
        else:
            raise ValueError("which must be 'left' or 'right'")
        
        return self.frame(triggers=triggers, duration_ms=duration_ms)
    
    def combo(self, *buttons: Button, interval_ms: float = 50) -> 'SequenceBuilder':
        """
        Press multiple buttons sequentially with interval between them.
        
        Example:
            # A, wait 50ms, B, wait 50ms, C
            seq.combo(Button.A, Button.B, Button.C, interval_ms=50)
        
        Args:
            buttons: Buttons to press in sequence
            interval_ms: Time between each button
        
        Returns:
            self (for chaining)
        """
        for btn in buttons:
            self.frame(buttons=[btn], duration_ms=interval_ms)
        return self
    
    def rapid_tap(self, button: Button, taps: int = 5, interval_ms: float = 100) -> 'SequenceBuilder':
        """
        Rapidly tap a button multiple times.
        
        Example:
            # Tap A 10 times, 100ms apart
            seq.rapid_tap(Button.A, taps=10, interval_ms=100)
        
        Args:
            button: Button to tap
            taps: Number of taps
            interval_ms: Time between taps
        
        Returns:
            self (for chaining)
        """
        for _ in range(taps):
            self.frame(buttons=[button], duration_ms=interval_ms // 2)
            self.frame(duration_ms=interval_ms // 2)
        return self
    
    def hold(self, button: Button, duration_ms: float) -> 'SequenceBuilder':
        """
        Hold a button for a duration.
        
        Args:
            button: Button to hold
            duration_ms: Duration to hold
        
        Returns:
            self (for chaining)
        """
        return self.frame(buttons=[button], duration_ms=duration_ms)
    
    def double_tap(self, button: Button, interval_ms: float = 200) -> 'SequenceBuilder':
        """
        Double-tap a button.
        
        Args:
            button: Button to tap
            interval_ms: Time between taps
        
        Returns:
            self (for chaining)
        """
        self.frame(buttons=[button], duration_ms=50)
        self.frame(duration_ms=interval_ms - 50)
        self.frame(buttons=[button], duration_ms=50)
        return self
    
    def build(self) -> Sequence:
        """
        Finalize and return the sequence.
        
        Returns:
            Completed Sequence object
        """
        self.sequence.duration_ms = self.current_time_ms
        return self.sequence


# Utility functions for common patterns

def create_button_spam(button: Button, 
                       presses: int = 10, 
                       interval_ms: float = 100,
                       name: str = None) -> Sequence:
    """Generate rapid button presses."""
    if name is None:
        name = f"spam_{button.name}_{presses}x"
    
    builder = SequenceBuilder(name, f"Rapidly press {button.name}")
    builder.rapid_tap(button, presses, interval_ms)
    return builder.build()


def create_stick_circle(radius: float = 1.0,
                        points: int = 32,
                        duration_per_point_ms: float = 50) -> Sequence:
    """Generate a full circle stick movement."""
    import math
    
    builder = SequenceBuilder("stick_circle", "Full rotation stick movement")
    
    for i in range(points):
        angle = (i / points) * math.pi * 2
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        builder.stick("right", x, y, duration_per_point_ms)
    
    return builder.build()


def create_stick_sine(amplitude: float = 1.0,
                      cycles: int = 2,
                      points_per_cycle: int = 20,
                      duration_per_point_ms: float = 50) -> Sequence:
    """Generate a sine wave stick movement."""
    import math
    
    builder = SequenceBuilder("stick_sine", f"Sine wave stick movement ({cycles} cycles)")
    
    total_points = cycles * points_per_cycle
    for i in range(total_points):
        angle = (i / points_per_cycle) * math.pi * 2
        y = amplitude * math.sin(angle)
        builder.stick("right", 0.0, y, duration_per_point_ms)
    
    return builder.build()


def load_and_modify(filepath: str, speed_factor: float = 1.0) -> Sequence:
    """Load a sequence and adjust all timings by a factor."""
    seq = Sequence.load(filepath)
    
    for frame in seq.frames:
        frame.timestamp_ms *= speed_factor
    
    seq.duration_ms *= speed_factor
    return seq
