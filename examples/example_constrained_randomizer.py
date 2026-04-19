"""
example_constrained_randomizer.py
Author: Created for constrained frame randomization gameplay

Demonstration of the ConstrainedFrameRandomizer.

This example only swaps inputs within their own category:
- Buttons swap positions with other buttons
- Analog sticks swap positions with other analog sticks
- Triggers swap positions with other triggers

This maintains proper neutral values and prevents unexpected behavior.

Controls:
  - Press HOME key: Randomize the mappings
  - Ctrl+C: Exit the program
"""

from XSerialOne.debug_viewer import DebugViewer
from XSerialOne.modules.xinput import XInputGenerator
from XSerialOne.extras.modules.constrained_frame_randomizer import ConstrainedFrameRandomizer
from XSerialOne.modules.deadzones import DeadzoneModifier
from XSerialOne.pipeline import InputPipeline
from pynput import keyboard
import serial.tools.list_ports


if __name__ == "__main__":
    # Get available COM ports
    ports = [p.device for p in serial.tools.list_ports.comports()]
    if not ports:
        raise SystemExit("No COM ports found.")
    
    print("Available COM ports:")
    for i, port in enumerate(ports):
        print(f"{i}: {port}")
    
    try:
        port_idx = int(input("Select port number: "))
        com_port = ports[port_idx]
    except (ValueError, IndexError):
        com_port = ports[0]
        print(f"Using default port: {com_port}")
    
    # Create the input pipeline
    pipeline = InputPipeline(com_port)
    
    # Add input generator (Xbox controller via XInput)
    xinput_gen = XInputGenerator()
    pipeline.add_generator(xinput_gen)
    
    # Add modifiers in order
    # 1. Apply deadzones to analog sticks
    deadzones_mod = DeadzoneModifier(deadzone_left=0.20, deadzone_right=0.15)
    pipeline.add_modifier(deadzones_mod)
    
    # 2. Randomize within categories on HOME key press
    randomizer_mod = ConstrainedFrameRandomizer(hotkey=keyboard.Key.home)
    pipeline.add_modifier(randomizer_mod)
    
    # Print usage info
    print("\n" + "="*60)
    print("Constrained Frame Randomizer Active")
    print("="*60)
    print("Press HOME key to randomize:")
    print("  - Buttons swap with buttons")
    print("  - Analog sticks swap with analog sticks")
    print("  - Triggers swap with triggers")
    print("Press Ctrl+C to stop\n")
    
    # Create debug viewer to see input vs output
    viewer = DebugViewer(
        left_tag="original input",
        show_second_screen=True,
        right_tag="randomized mapping"
    )
    viewer.attach_to_pipeline(pipeline)
    viewer.start()
    
    try:
        pipeline.run_loop()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        viewer.stop()
