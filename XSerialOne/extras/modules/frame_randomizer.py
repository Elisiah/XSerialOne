"""
frame_randomizer.py
Author: Created for dynamic frame randomization gameplay

A modifier that randomizes button and axis mappings on hotkey press.
Perfect for games where you need to learn controller mappings dynamically.
When the hotkey is pressed, all button and axis outputs are randomly shuffled,
forcing the player to figure out the new mapping in real-time.

Supports full randomization including converting buttons to axes and vice versa,
with smooth ramp-up for button->axis conversion.
"""

import logging
import random
import threading
import time
from typing import Dict, Tuple

from XSerialOne.base import BaseModifier, FrameState

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

logger = logging.getLogger("frame_randomizer")


class FrameRandomizerModifier(BaseModifier):
    """
    Randomizes button and axis mappings on hotkey press.
    
    When the configured hotkey is pressed, the modifier generates a new
    random mapping that shuffles how inputs are presented. This forces
    the player to adapt and figure out the new button/axis layout.
    
    Supports full randomization including buttons mapped to axes with smooth
    ramp-up, and axes mapped to buttons with threshold detection.
    
    Args:
        hotkey: pynput keyboard.Key to trigger randomization (default: HOME)
        randomize_buttons: Whether to randomize button mappings (default: True)
        randomize_axes: Whether to randomize axis mappings (default: True)
        button_ramp_time: Time in seconds to ramp button->axis (default: 0.1s)
        axis_button_threshold: Threshold for axis->button conversion (default: 0.0)
    """
    
    def __init__(
        self,
        hotkey=keyboard.Key.home if HAS_PYNPUT else None,
        randomize_buttons: bool = True,
        randomize_axes: bool = True,
        button_ramp_time: float = 0.1,
        axis_button_threshold: float = 0.0,
    ):
        super().__init__()
        
        if not HAS_PYNPUT:
            raise ImportError(
                "pynput is required for FrameRandomizerModifier. "
                "Install with: pip install pynput"
            )
        
        self.hotkey = hotkey
        self.randomize_buttons = randomize_buttons
        self.randomize_axes = randomize_axes
        self.button_ramp_time = button_ramp_time
        self.axis_button_threshold = axis_button_threshold
        
        # Mappings: input index -> (output_type, output_index)
        # output_type: 'button' or 'axis'
        self.input_mappings: Dict[Tuple[str, int], Tuple[str, int]] = {}
        self._rebuild_mappings()
        
        # Track button ramp state: output_axis_idx -> (press_time, is_pressed)
        self.button_ramps: Dict[int, Dict] = {}
        
        # Hotkey listener
        self.listener = None
        self.lock = threading.Lock()
        
        # Start listening for hotkey
        self._start_listener()
    
    def _start_listener(self):
        """Start the global keyboard listener."""
        try:
            self.listener = keyboard.Listener(on_press=self._on_key_press)
            self.listener.start()
            logger.info(f"Frame randomizer listening for {self.hotkey} hotkey")
        except Exception as e:
            logger.error(f"Failed to start keyboard listener: {e}")
    
    def _on_key_press(self, key):
        """Called when any key is pressed."""
        try:
            if key == self.hotkey:
                self._randomize_mapping()
        except AttributeError:
            # key doesn't have the hotkey attribute, ignore
            pass
    
    def _rebuild_mappings(self):
        """Rebuild the complete input->output mappings."""
        self.input_mappings = {}
        
        # Create list of all input sources: buttons (0-9) and axes (0-5)
        all_inputs = [(('button', i) for i in range(10))]
        all_inputs.extend([(('axis', i) for i in range(6))])
        
        # Create list of all output targets: buttons (0-9) and axes (0-5)
        all_outputs = [(('button', i) for i in range(10))]
        all_outputs.extend([(('axis', i) for i in range(6))])
        
        # Flatten the lists
        all_inputs = list(all_inputs[0]) + list(all_inputs[1])
        all_outputs = list(all_outputs[0]) + list(all_outputs[1])
        
        if self.randomize_buttons or self.randomize_axes:
            # Shuffle outputs while keeping inputs in order
            random.shuffle(all_outputs)
            for input_item, output_item in zip(all_inputs, all_outputs):
                self.input_mappings[input_item] = output_item
            
            # Log the mapping
            logger.info("New randomized mapping:")
            for inp, out in self.input_mappings.items():
                logger.info(f"  {inp[0]}{inp[1]:02d} -> {out[0]}{out[1]:02d}")
        else:
            # Identity mapping
            for inp in all_inputs:
                self.input_mappings[inp] = inp
    
    def _randomize_mapping(self):
        """Generate a new random mapping."""
        with self.lock:
            self._rebuild_mappings()
            self.button_ramps.clear()
    
    def _get_button_ramp_value(self, axis_idx: int, button_pressed: bool, now: float) -> float:
        """
        Get the ramped axis value for a button->axis conversion.
        
        Handles both analog sticks (neutral=0) and triggers (neutral=-1).
        
        Args:
            axis_idx: Output axis index (0-5)
                     0-3: Analog sticks (neutral at 0)
                     4-5: Triggers (neutral at -1)
            button_pressed: Whether the button is currently pressed
            now: Current time
            
        Returns:
            Axis value from neutral to 1 (fully pressed)
        """
        if axis_idx not in self.button_ramps:
            self.button_ramps[axis_idx] = {"start_time": None, "was_pressed": False}
        
        state = self.button_ramps[axis_idx]
        
        # Button transitioned from released to pressed
        if button_pressed and not state["was_pressed"]:
            state["start_time"] = now
        
        state["was_pressed"] = button_pressed
        
        # Determine neutral position based on axis type
        is_trigger = axis_idx >= 4  # Axes 4-5 are triggers
        neutral = -1.0 if is_trigger else 0.0
        
        if not button_pressed:
            # Button released: return to neutral
            return neutral
        
        # Button is pressed: ramp from neutral to 1
        if state["start_time"] is None:
            state["start_time"] = now
        
        elapsed = now - state["start_time"]
        if elapsed >= self.button_ramp_time:
            # Fully ramped
            return 1.0
        
        # Interpolate between neutral and 1
        progress = elapsed / self.button_ramp_time
        return neutral + ((1.0 - neutral) * progress)
    
    def update(self, state: FrameState) -> FrameState:
        """Apply the current random mapping to the frame."""
        with self.lock:
            remapped_buttons = [False] * 10
            # Initialize axes to neutral: 0.0 for sticks (0-3), -1.0 for triggers (4-5)
            remapped_axes = [0.0, 0.0, 0.0, 0.0, -1.0, -1.0]
            
            now = time.perf_counter()
            
            # Process all input buttons
            for input_idx, button_val in enumerate(state.buttons):
                input_key = ('button', input_idx)
                if input_key in self.input_mappings:
                    output_type, output_idx = self.input_mappings[input_key]
                    
                    if output_type == 'button':
                        # Button -> Button (straight copy)
                        remapped_buttons[output_idx] = button_val
                    else:  # output_type == 'axis'
                        # Button -> Axis (with ramp-up from neutral to 1)
                        remapped_axes[output_idx] = self._get_button_ramp_value(
                            output_idx, button_val, now
                        )
            
            # Process all input axes
            for input_idx, axis_val in enumerate(state.axes):
                input_key = ('axis', input_idx)
                if input_key in self.input_mappings:
                    output_type, output_idx = self.input_mappings[input_key]
                    
                    if output_type == 'axis':
                        # Axis -> Axis (straight copy)
                        value = axis_val
                        # For trigger output axes, ensure neutral at -1 (not 0 from stick inputs)
                        if output_idx >= 4 and value == 0.0:
                            value = -1.0
                        remapped_axes[output_idx] = value
                    else:  # output_type == 'button'
                        # Axis -> Button (threshold: > threshold = pressed)
                        remapped_buttons[output_idx] = axis_val > self.axis_button_threshold
            
            return FrameState(
                buttons=tuple(remapped_buttons),
                axes=tuple(remapped_axes),
                dpad=state.dpad
            )
    
    def __del__(self):
        """Clean up listener on deletion."""
        if self.listener:
            self.listener.stop()


class AxisOnlyFrameRandomizer(FrameRandomizerModifier):
    """
    Randomizes only axis mappings on hotkey press.
    Better for games where button positions matter but analog sticks don't.
    
    Args:
        hotkey: pynput keyboard.Key to trigger randomization (default: HOME)
    """
    
    def __init__(self, hotkey=keyboard.Key.home if HAS_PYNPUT else None):
        super().__init__(
            hotkey=hotkey,
            randomize_buttons=False,
            randomize_axes=True,
        )


class ButtonOnlyFrameRandomizer(FrameRandomizerModifier):
    """
    Randomizes only button mappings on hotkey press.
    Better for games where analog sticks matter but buttons don't.
    
    Args:
        hotkey: pynput keyboard.Key to trigger randomization (default: HOME)
    """
    
    def __init__(self, hotkey=keyboard.Key.home if HAS_PYNPUT else None):
        super().__init__(
            hotkey=hotkey,
            randomize_buttons=True,
            randomize_axes=False,
        )
