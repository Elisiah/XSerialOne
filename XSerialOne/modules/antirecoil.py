"""
antirecoil.py
Author: Ellie V.

Anti-recoil compensation module for the XSerialOne framework.

This module provides automatic recoil compensation for shooting games,
adjusting the right analog stick position based on trigger input to
counter weapon recoil patterns. The modifier preserves original stick
movement while adding vertical compensation when firing.
"""

import math
from XSerialOne.base import BaseModifier, FrameState
from XSerialOne.frame_constants import Axis

class BasicAntiRecoilModifier(BaseModifier):
    def __init__(self):
        super().__init__()
        self.recoil_strength = 0.3  
        self.trigger_threshold = 0.1  
        
    def update(self, state: FrameState) -> FrameState:
        axes = list(state.axes)
        
        right_x = axes[Axis.RIGHTSTICKX] 
        right_y = axes[Axis.RIGHTSTICKY] 
        
        rt = axes[Axis.RIGHTTRIGGER]
        if rt >= self.trigger_threshold:
            recoil_force = abs(self.recoil_strength) * (rt / 1.0)
            current_magnitude = math.sqrt(right_x * right_x + right_y * right_y)
            
            if current_magnitude > 0.01: 
                axes[Axis.RIGHTSTICKX] = right_x  
                axes[Axis.RIGHTSTICKY] = right_y + recoil_force  
            else:
                axes[Axis.RIGHTSTICKY] = axes[Axis.RIGHTSTICKY] + recoil_force

        return FrameState(buttons=state.buttons, axes=tuple(axes), dpad=state.dpad)