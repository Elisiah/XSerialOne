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

import os

import serial.tools.list_ports

from XSerialOne.extras.flashbang import FlashbangOverlay
from XSerialOne.extras.modules.twitch_chat import (
    EventSubListener,
    TwitchChatServer,
    TwitchEventQueue,
    TwitchInputModifier,
)
from XSerialOne.modules.antirecoil import BasicAntiRecoilModifier
from XSerialOne.modules.deadzones import DeadzoneModifier
from XSerialOne.modules.xinput import XInputGenerator
from XSerialOne.pipeline import InputPipeline

if __name__ == "__main__":
    TWITCH_OAUTH = os.environ["TWITCH_OAUTH"]
    TWITCH_CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
    TWITCH_USERNAME = os.environ.get("TWITCH_USERNAME", "")
    TWITCH_CHANNEL = os.environ.get("TWITCH_CHANNEL", TWITCH_USERNAME)
    TWITCH_BROADCASTER_ID = int(os.environ["TWITCH_BROADCASTER_ID"])

    queue = TwitchEventQueue()

    # --- Start Twitch Chat (IRC) ---
    chat = TwitchChatServer(
        oauth_token=TWITCH_OAUTH,
        username=TWITCH_USERNAME,
        channel=TWITCH_CHANNEL,
        queue=queue,
    )
    chat.start()

    # --- Start EventSub ---
    eventsub = EventSubListener(
        oauth_token=TWITCH_OAUTH,
        client_id=TWITCH_CLIENT_ID,
        broadcaster_id=TWITCH_BROADCASTER_ID,
        queue=queue,
    )
    eventsub.start()

    # --- Start Blooper Overlay ---
    flashbang = FlashbangOverlay(
        queue=queue,
        reward_name="Flashbang",  # Name of your channel points reward
        animation_duration=5.0,  # How long the ink drips
        width=1920,  # Match your stream resolution
        height=1080,
    )
    flashbang.start()

    twitch_mod = TwitchInputModifier(queue)
    xinput_gen = XInputGenerator()
    antirecoil_mod = BasicAntiRecoilModifier()
    deadzones_mod = DeadzoneModifier(deadzone_left=0.20, deadzone_right=0.15)

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
    #pipeline.add_modifier(deadzones_mod)
    pipeline.add_modifier(twitch_mod)
    #pipeline.add_modifier(HairTriggers(threshold=-0.9))

    print("Starting controller passthrough. Press Ctrl+C to stop.")
    print("Press PAUSE key to pause/resume Twitch inputs.")
    #viewer = TwitchDebugViewer(left_tag="", right_tag="", width=800, height=320)
    #viewer.attach_to_pipeline(pipeline, twitch_server=twitch, decay_window=0.5)
    #viewer.start()

    try:
        pipeline.run_loop()
    finally:
        #viewer.stop()
        flashbang.stop()
        twitch_mod.stop_keyboard_listener()
        chat.stop()
        eventsub.stop()
