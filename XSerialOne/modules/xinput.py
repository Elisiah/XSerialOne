"""
xinput.py
Author: Ellie V.

Windows XInput interface for the XSerialOne framework.

This module provides Xbox controller input support through Windows XInput,
offering high-performance, low-latency access to controller states. It handles
controller connection management, input normalization, and error recovery
for reliable controller input processing.
"""

import ctypes
import logging
from typing import Optional, Dict, Any
from XSerialOne.base import BaseGenerator, FrameState

logger = logging.getLogger(__name__)

class XInputError(Exception):
    """Base exception for XInput-related errors."""
    pass

class XInputGenerator(BaseGenerator):
    """Generator that reads input from an Xbox controller using XInput."""
    
    def __init__(self, controller_id: int = 0):
        """Initialize XInput generator.
        
        Args:
            controller_id: Index of the controller to read (0-3)
        
        Raises:
            XInputError: If no XInput DLL could be loaded
        """
        super().__init__()
        self.controller_id = controller_id
        self.xinput = self._load_xinput_dll()
        if not self.xinput:
            raise XInputError("No XInput DLL could be loaded")

        # Button bit masks
        self.BUTTON_MAP = {
            "A": 0x1000, "B": 0x2000, "X": 0x4000, "Y": 0x8000,
            "LB": 0x0100, "RB": 0x0200, "BACK": 0x0020, "START": 0x0010,
            "LS": 0x0040, "RS": 0x0080
        }
        
        # Constants
        self.ERROR_SUCCESS = 0
        self.ERROR_DEVICE_NOT_CONNECTED = 1167
        self._last_error = self.ERROR_SUCCESS
        
    @staticmethod
    def _load_xinput_dll() -> Optional[Any]:
        """Attempt to load an XInput DLL.
        
        Returns:
            The loaded DLL object or None if no DLL could be loaded
        """
        dll_names = ['xinput1_4', 'xinput9_1_0', 'xinput1_3']
        for dll in dll_names:
            try:
                return getattr(ctypes.windll, dll)
            except (OSError, AttributeError) as e:
                logger.debug(f"Failed to load {dll}: {e}")
        return None
        
    def is_connected(self) -> bool:
        """Check if the controller is currently connected.
        
        Returns:
            True if the controller is connected, False otherwise
        """
        state = ctypes.create_string_buffer(20)
        result = self.xinput.XInputGetState(self.controller_id, ctypes.byref(state))
        self._last_error = result
        return result == self.ERROR_SUCCESS
        
    def _normalize_stick(self, value: int, scale: float = 32768.0) -> float:
        """Normalize a stick axis value to the range [-1.0, 1.0].
        
        Args:
            value: Raw stick value
            scale: Maximum value for normalization
            
        Returns:
            Normalized value between -1.0 and 1.0
        """
        try:
            return max(-1.0, min(1.0, float(value) / scale))
        except (TypeError, ValueError):
            return 0.0
            
    def _normalize_trigger(self, value: int) -> float:
        """Normalize a trigger value to the range [-1.0, 1.0].
        
        Args:
            value: Raw trigger value
            
        Returns:
            Normalized value between -1.0 and 1.0
        """
        try:
            return max(-1.0, min(1.0, (float(value) - 127.5) / 127.5))
        except (TypeError, ValueError):
            return 0.0

    def read_xinput(self) -> Dict[str, Any]:
        """Read the current state of the controller.
        
        Returns:
            Dict containing buttons, axes, and dpad states
        """
        state = ctypes.create_string_buffer(20)
        buttons = [False]*10
        axes = [0.0]*6
        dpad = (0, 0)

        try:
            res = self.xinput.XInputGetState(self.controller_id, ctypes.byref(state))
            self._last_error = res
            
            if res == self.ERROR_SUCCESS and len(state.raw) >= 16:
                try:
                    wButtons = int.from_bytes(state.raw[4:6], 'little')
                    
                    # Map buttons using order from BUTTON_MAP
                    for i, (_, mask) in enumerate(self.BUTTON_MAP.items()):
                        buttons[i] = bool(wButtons & mask)

                    # Process triggers with safety checks
                    lt = self._normalize_trigger(state.raw[6])
                    rt = self._normalize_trigger(state.raw[7])
                    
                    # Process sticks with safety checks
                    try:
                        leftX = self._normalize_stick(
                            ctypes.c_short.from_buffer_copy(state.raw[8:10]).value)
                        leftY = -self._normalize_stick(
                            ctypes.c_short.from_buffer_copy(state.raw[10:12]).value)
                        rightX = self._normalize_stick(
                            ctypes.c_short.from_buffer_copy(state.raw[12:14]).value)
                        rightY = -self._normalize_stick(
                            ctypes.c_short.from_buffer_copy(state.raw[14:16]).value)
                    except (ValueError, BufferError) as e:
                        logger.warning(f"Error processing stick values: {e}")
                        leftX = leftY = rightX = rightY = 0.0

                    axes = [leftX, leftY, rightX, rightY, lt, rt]

                    # Process DPAD
                    hx, hy = 0, 0
                    if wButtons & 0x0001: hy = 1   # DPAD UP
                    if wButtons & 0x0002: hy = -1  # DPAD DOWN
                    if wButtons & 0x0004: hx = -1  # DPAD LEFT
                    if wButtons & 0x0008: hx = 1   # DPAD RIGHT
                    dpad = (hx, hy)
                    
                except (IndexError, ValueError) as e:
                    logger.error(f"Error processing XInput state: {e}")
            
            elif res == self.ERROR_DEVICE_NOT_CONNECTED:
                logger.debug(f"Controller {self.controller_id} not connected")
                
        except Exception as e:
            logger.error(f"XInput read failed: {e}")

        return {"buttons": buttons, "axes": axes, "dpad": dpad}

    def generate(self) -> FrameState:
        """Generate a new frame state from the current controller state.
        
        Returns:
            FrameState containing the current controller state or default state if an error occurs
        """
        if not self.xinput:
            logger.error("No XInput DLL available")
            return self.default_state()
            
        try:
            raw = self.read_xinput()
            return FrameState.from_dict(raw)
        except Exception as e:
            logger.error(f"Error generating frame state: {e}")
            return self.default_state()