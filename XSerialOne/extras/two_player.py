"""
example.py
Author: Ellie V.

Demonstration script for the XSerialOne framework.

This example reads input from an Xbox controller via XInput,
passes the data through a configurable chain of input modifiers
(e.g., deadzones, anti-recoil), and transmits the resulting 
state to a custom XSerialOne hardware device that simulates 
controller input on an Xbox Series X/S console.
"""
import serial.tools.list_ports

from XSerialOne.debug_viewer import DebugViewer
from XSerialOne.extras.modules.twoplayer import MergeRemoteModifier, RelayServer
from XSerialOne.modules.antirecoil import BasicAntiRecoilModifier
from XSerialOne.modules.deadzones import DeadzoneModifier
from XSerialOne.modules.xinput import XInputGenerator
from XSerialOne.pipeline import InputPipeline

if __name__ == "__main__":
    relay = RelayServer(ws_port=8765)
    relay.start()

    xinput_gen = XInputGenerator()
    antirecoil_mod = BasicAntiRecoilModifier()
    deadzones_mod = DeadzoneModifier(deadzone_left=0.20, deadzone_right=0.15)
    merge_mod = MergeRemoteModifier(relay_server=relay)

    ports = [p.device for p in serial.tools.list_ports.comports()]
    if not ports:
        raise SystemExit("No COM ports found.")
    
    print("Available COM ports:")
    for i, port in enumerate(ports):
        print(f"{i}: {port}")
    
    try:
        port_idx = int(input("Select port number: "))
        com_port = ports[port_idx]
    except Exception:
        com_port = ports[0]
        print(f"Using default port: {com_port}")
    pipeline = InputPipeline(com_port)
    pipeline.add_generator(xinput_gen)
    #pipeline.add_modifier(antirecoil_mod)
    pipeline.add_modifier(deadzones_mod)
    pipeline.add_modifier(merge_mod)
    #pipeline.add_modifier(HairTriggers(threshold=-0.9))

    print("Starting controller passthrough. Press Ctrl+C to stop.")
    viewer = DebugViewer(left_tag="Me", show_second_screen=True, right_tag="Both")
    viewer.attach_to_pipeline(pipeline)
    viewer.start()

    try:
        pipeline.run_loop()
    finally:
        viewer.stop()
