"""
deadzones.py
Author: Ellie V.

Input deadzone processing for the XSerialOne framework.

This module provides input processing modifiers for handling controller
deadzone and trigger response curves. It includes both standard radial
deadzones for analog sticks and hair trigger functionality for more
responsive trigger inputs.
"""

from XSerialOne.base import BaseModifier, FrameState
from XSerialOne.frame_constants import Axis

class DeadzoneModifier(BaseModifier):
    """
    Applies deadzones to joystick axes in the FrameState.
    Input per stick is [0, 1] representing the deadzone radius.
    """

    def __init__(self, deadzone_left=0.2, deadzone_right=0.2):
        super().__init__()
        self.deadzone_left = deadzone_left
        self.deadzone_right = deadzone_right

    def update(self, state: FrameState) -> FrameState:
        axes = list(state.axes)
        deadzones = [self.deadzone_left] * 2 + [self.deadzone_right] * 2
        
        new_axes = [
            0.0 if abs(axes[i]) < deadzones[i] else axes[i]
            for i in range(4)
        ]
        new_axes.extend(axes[4:])
        
        return FrameState(buttons=state.buttons, axes=tuple(new_axes), dpad=state.dpad)
    

class HairTriggers(BaseModifier):
    def __init__(self, threshold=0.1):
        super().__init__()
        self.threshold = threshold

    def update(self, state: FrameState) -> FrameState:
        axes = list(state.axes)
        rt = axes[Axis.RIGHTTRIGGER]
        if rt > self.threshold:
            axes[Axis.RIGHTTRIGGER] = 1.0
        else:
            axes[Axis.RIGHTTRIGGER] = -1.0
        return FrameState(buttons=state.buttons, axes=tuple(axes), dpad=state.dpad)