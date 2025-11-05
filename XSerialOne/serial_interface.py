"""
serial_interface.py
Author: Ellie V.

Serial communication interface for the XSerialOne framework.

This module handles the low-level communication with XSerialOne hardware
devices over serial connections. It implements the custom protocol for
transmitting controller state data, including button states, analog
values, and d-pad positions.
"""

import struct
import serial
from dataclasses import dataclass
from XSerialOne.base import FrameState

@dataclass
class Packet:
    buttons: int
    axes: list[float]
    dpad_code: int

    HEADER = 0xFF

    def pack(self) -> bytes:
        ax = (self.axes + [0.0]*6)[:6]
        payload = struct.pack('<HffffffB', self.buttons, *ax, self.dpad_code)
        checksum = sum(payload) & 0xFF
        return struct.pack('<B', self.HEADER) + payload + struct.pack('<B', checksum)


class SerialInterface:
    def __init__(self, port, baud=115200):
        if not port or (isinstance(port, str) and port.upper().startswith("MOCK")):
            self.ser = None
            print(f"[SerialInterface] Mock/no-serial mode for port={port}")
        else:
            if serial is None:
                raise RuntimeError("pyserial is required to open real serial ports")
            self.ser = serial.Serial(port, baud, timeout=0.1)
            print(f"[SerialInterface] Connected to {port}")

    def send_frame(self, frame_state: FrameState):
        if not isinstance(frame_state, FrameState):
            raise TypeError("Expected FrameState instance")

        packet = Packet(
            buttons=self.buttons_to_bitmask(frame_state.buttons),
            axes=list(frame_state.axes),
            dpad_code=self.dpad_encode(frame_state.dpad)
        )

        if not self.ser:
            raise RuntimeError("Serial port not open")

        self.ser.write(packet.pack())

    def buttons_to_bitmask(self, buttons):
        mask = 0
        for i, pressed in enumerate(buttons):
            if pressed:
                mask |= (1 << i)
        return mask & 0xFFFF

    def dpad_encode(self, dpad):
        hx, hy = dpad
        return (hx + 1) + (hy + 1) * 3

    def close(self):
        if self.ser:
            self.ser.close()