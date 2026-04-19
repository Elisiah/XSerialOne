import time

from XSerialOne.base import BaseModifier, FrameState
from XSerialOne.frame_constants import Axis, Button, Dpad
from XSerialOne.macro_builder import MacroBuilder
from XSerialOne.macro_system import MacroManager


class AntiAFKModifier(BaseModifier):
    def __init__(self):
        super().__init__()
        self.macro_manager = MacroManager()
        self._setup_anti_afk_macro()
        
    def _setup_anti_afk_macro(self):
        """Setup anti-afk macro with proper toggle behavior"""
        anti_afk = (MacroBuilder("anti_afk")
            .activate_on_combo(Button.LB, dpad=Dpad.DOWN)
            .stick(Axis.LEFTSTICKY, -1.0)
            .trigger(Axis.LEFTTRIGGER, 1.0)
            .wait(2.0)
            .stick(Axis.LEFTSTICKY, 1.0)
            .wait(2.0)
            .build(loop=True)
        )
        
        self.macro_manager.register_macro(anti_afk)
        
    def update(self, state: FrameState) -> FrameState:
        current_time = time.monotonic()
        return self.macro_manager.update(current_time, state)