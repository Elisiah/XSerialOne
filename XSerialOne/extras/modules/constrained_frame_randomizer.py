"""
constrained_frame_randomizer.py
Author: Created for constrained frame randomization gameplay

A simpler randomizer that only swaps inputs within their own category.
Buttons only swap with buttons, analog sticks only swap with analog sticks,
and triggers only swap with triggers. This maintains proper neutral values.
"""

import logging
import random
import threading
from typing import List

from XSerialOne.base import BaseModifier, FrameState

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

logger = logging.getLogger("constrained_frame_randomizer")


class ConstrainedFrameRandomizer(BaseModifier):
    """
    Randomizes inputs within their own category on hotkey press.
    
    - Buttons (0-9) shuffle with other buttons only
    - Analog sticks (0-3) shuffle with other analog sticks only
    - Triggers (4-5) shuffle with other triggers only
    
    This keeps neutral values correct:
    - Buttons: on/off
    - Analog sticks: neutral at 0
    - Triggers: neutral at -1
    
    Args:
        hotkey: pynput keyboard.Key to trigger randomization (default: HOME)
    """
    
    def __init__(self, hotkey=keyboard.Key.home if HAS_PYNPUT else None):
        super().__init__()
        
        if not HAS_PYNPUT:
            raise ImportError(
                "pynput is required for ConstrainedFrameRandomizer. "
                "Install with: pip install pynput"
            )
        
        self.hotkey = hotkey
        
        # Button mapping: input_button_idx -> output_button_idx
        self.button_mapping: List[int] = list(range(10))
        
        # Analog stick mapping: input_stick_idx -> output_stick_idx (0-3)
        self.analog_mapping: List[int] = list(range(4))
        
        # Trigger mapping: input_trigger_idx -> output_trigger_idx (0-1 -> 4-5)
        self.trigger_mapping: List[int] = list(range(2))
        
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
            logger.info(f"Constrained randomizer listening for {self.hotkey} hotkey")
        except Exception as e:
            logger.error(f"Failed to start keyboard listener: {e}")
    
    def _on_key_press(self, key):
        """Called when any key is pressed."""
        try:
            if key == self.hotkey:
                self._randomize_mapping()
        except AttributeError:
            pass
    
    def _randomize_mapping(self):
        """Generate new random mappings within each category."""
        with self.lock:
            # Randomize buttons
            self.button_mapping = list(range(10))
            random.shuffle(self.button_mapping)
            logger.info(f"Randomized buttons: {self.button_mapping}")
            
            # Randomize analog sticks
            self.analog_mapping = list(range(4))
            random.shuffle(self.analog_mapping)
            logger.info(f"Randomized analog sticks: {self.analog_mapping}")
            
            # Randomize triggers
            self.trigger_mapping = list(range(2))
            random.shuffle(self.trigger_mapping)
            logger.info(f"Randomized triggers: {self.trigger_mapping}")
    
    def update(self, state: FrameState) -> FrameState:
        """Apply the current random mapping to the frame."""
        with self.lock:
            remapped_buttons = [False] * 10
            remapped_axes = [0.0, 0.0, 0.0, 0.0, -1.0, -1.0]
            
            # Remap buttons (0-9)
            for input_idx, button_val in enumerate(state.buttons):
                output_idx = self.button_mapping[input_idx]
                remapped_buttons[output_idx] = button_val
            
            # Remap analog sticks (axes 0-3)
            for input_idx in range(4):
                output_idx = self.analog_mapping[input_idx]
                remapped_axes[output_idx] = state.axes[input_idx]
            
            # Remap triggers (axes 4-5 -> mapping indices 0-1)
            for i in range(2):
                input_idx = 4 + i
                trigger_output_idx = 4 + self.trigger_mapping[i]
                remapped_axes[trigger_output_idx] = state.axes[input_idx]
            
            return FrameState(
                buttons=tuple(remapped_buttons),
                axes=tuple(remapped_axes),
                dpad=state.dpad
            )
    
    def __del__(self):
        """Clean up listener on deletion."""
        if self.listener:
            self.listener.stop()


class StickOnlyRandomizer(BaseModifier):
    """
    Randomizes only analog stick mappings (axes 0-3).
    Buttons and triggers remain unmapped.
    
    Args:
        hotkey: pynput keyboard.Key to trigger randomization (default: HOME)
    """
    
    def __init__(self, hotkey=keyboard.Key.home if HAS_PYNPUT else None):
        super().__init__()
        
        if not HAS_PYNPUT:
            raise ImportError(
                "pynput is required for StickOnlyRandomizer. "
                "Install with: pip install pynput"
            )
        
        self.hotkey = hotkey
        self.analog_mapping: List[int] = list(range(4))
        
        self.listener = None
        self.lock = threading.Lock()
        self._start_listener()
    
    def _start_listener(self):
        """Start the global keyboard listener."""
        try:
            self.listener = keyboard.Listener(on_press=self._on_key_press)
            self.listener.start()
            logger.info(f"Stick-only randomizer listening for {self.hotkey} hotkey")
        except Exception as e:
            logger.error(f"Failed to start keyboard listener: {e}")
    
    def _on_key_press(self, key):
        """Called when any key is pressed."""
        try:
            if key == self.hotkey:
                self._randomize_mapping()
        except AttributeError:
            pass
    
    def _randomize_mapping(self):
        """Generate new random mapping for analog sticks."""
        with self.lock:
            self.analog_mapping = list(range(4))
            random.shuffle(self.analog_mapping)
            logger.info(f"Randomized analog sticks: {self.analog_mapping}")
    
    def update(self, state: FrameState) -> FrameState:
        """Apply the stick mapping to the frame."""
        with self.lock:
            remapped_axes = list(state.axes)
            
            # Remap analog sticks (axes 0-3)
            temp_axes = [state.axes[i] for i in range(4)]
            for input_idx in range(4):
                output_idx = self.analog_mapping[input_idx]
                remapped_axes[output_idx] = temp_axes[input_idx]
            
            return FrameState(
                buttons=state.buttons,
                axes=tuple(remapped_axes),
                dpad=state.dpad
            )
    
    def __del__(self):
        """Clean up listener on deletion."""
        if self.listener:
            self.listener.stop()


class ButtonOnlyRandomizer(BaseModifier):
    """
    Randomizes only button mappings (0-9).
    Analog sticks and triggers remain unmapped.
    
    Args:
        hotkey: pynput keyboard.Key to trigger randomization (default: HOME)
    """
    
    def __init__(self, hotkey=keyboard.Key.home if HAS_PYNPUT else None):
        super().__init__()
        
        if not HAS_PYNPUT:
            raise ImportError(
                "pynput is required for ButtonOnlyRandomizer. "
                "Install with: pip install pynput"
            )
        
        self.hotkey = hotkey
        self.button_mapping: List[int] = list(range(10))
        
        self.listener = None
        self.lock = threading.Lock()
        self._start_listener()
    
    def _start_listener(self):
        """Start the global keyboard listener."""
        try:
            self.listener = keyboard.Listener(on_press=self._on_key_press)
            self.listener.start()
            logger.info(f"Button-only randomizer listening for {self.hotkey} hotkey")
        except Exception as e:
            logger.error(f"Failed to start keyboard listener: {e}")
    
    def _on_key_press(self, key):
        """Called when any key is pressed."""
        try:
            if key == self.hotkey:
                self._randomize_mapping()
        except AttributeError:
            pass
    
    def _randomize_mapping(self):
        """Generate new random mapping for buttons."""
        with self.lock:
            self.button_mapping = list(range(10))
            random.shuffle(self.button_mapping)
            logger.info(f"Randomized buttons: {self.button_mapping}")
    
    def update(self, state: FrameState) -> FrameState:
        """Apply the button mapping to the frame."""
        with self.lock:
            remapped_buttons = [False] * 10
            
            # Remap buttons
            for input_idx, button_val in enumerate(state.buttons):
                output_idx = self.button_mapping[input_idx]
                remapped_buttons[output_idx] = button_val
            
            return FrameState(
                buttons=tuple(remapped_buttons),
                axes=state.axes,
                dpad=state.dpad
            )
    
    def __del__(self):
        """Clean up listener on deletion."""
        if self.listener:
            self.listener.stop()
