"""
pipeline.py
Author: Ellie V.

Input processing pipeline for the XSerialOne framework.

This module orchestrates the flow of controller input data through the system,
managing input generators, applying modifier chains, and handling serial
communication with XSerialOne hardware. It provides a flexible pipeline
architecture for real-time input processing and modification.
"""

import time
from XSerialOne.serial_interface import SerialInterface

class InputPipeline:
    def __init__(self, serial_port=None, baud=115200, send_interval=0.005):
        """
        Handles generators -> modifiers -> serial output
        """
        self.generators = []
        self.modifiers = []
        self.send_interval = send_interval
        self.last_send = 0

        self.serial = SerialInterface(serial_port, baud) if serial_port else None

        self._on_generate_callbacks = []
        self._on_post_mod_callbacks = []

    def add_generator(self, gen):
        self.generators.append(gen)

    def add_modifier(self, mod):
        self.modifiers.append(mod)

    def add_generate_callback(self, cb):
        """Register a callback called after a generator produces a FrameState.

        Callback signature: cb(frame_state)
        """
        self._on_generate_callbacks.append(cb)

    def add_post_mod_callback(self, cb):
        """Register a callback called after modifiers have been applied.

        Callback signature: cb(frame_state)
        """
        self._on_post_mod_callbacks.append(cb)

    def combine_generators(self):
        """
        Combine multiple generators.
        Default: take first generator.
        Can override for averaging multiple controllers.
        """
        if not self.generators:
            return None
        
        # Take first combination example
        state = self.generators[0].generate()
        return state

    def apply_modifiers(self, state):
        """
        Apply all modifier modules in sequence
        """
        for mod in self.modifiers:
            state = mod.update(state)
        return state

    def update(self):
        """
        Generate a frame, apply modifiers, and send via SerialInterface if configured.
        """
        state = self.combine_generators()
        if state is None:
            return None

        for cb in list(self._on_generate_callbacks):
            try:
                cb(state)
            except Exception:
                pass

        state = self.apply_modifiers(state)

        for cb in list(self._on_post_mod_callbacks):
            try:
                cb(state)
            except Exception:
                pass

        now = time.time()
        if self.serial and now - self.last_send >= self.send_interval:
            self.serial.send_frame(state)
            self.last_send = now

        return state

    def run_loop(self):
        """
        Continuous loop for pipeline updates
        """
        try:
            while True:
                self.update()
                time.sleep(0.001)
        except KeyboardInterrupt:
            if self.serial:
                self.serial.close()
            print("Pipeline stopped")
