import threading
from XSerialOne.base import BaseModifier, FrameState
import queue
import time

class TwitchChatListener(threading.Thread):
    def __init__(self, channel, queue_size=50):
        super().__init__(daemon=True)
        self.channel = channel
        self.msg_queue = queue.Queue(maxsize=queue_size)
        self.running = True

    def run(self):
        # Pseudocode: connect to Twitch IRC or API
        while self.running:
            msg = self.get_message()  # blocking call or polling
            if msg:
                try:
                    self.msg_queue.put_nowait(msg)
                except queue.Full:
                    pass

    def get_message(self):
        # Replace with real Twitch API read
        time.sleep(0.1)
        return None  # or {"user":"xyz","msg":"left"}

    def stop(self):
        self.running = False

class TwitchChatModifier(BaseModifier):
    def __init__(self, listener: TwitchChatListener):
        super().__init__()
        self.listener = listener

    def update(self, state: FrameState) -> FrameState:
        try:
            msg = self.listener.msg_queue.get_nowait()
        except queue.Empty:
            return state

        axes = list(state.axes)
        if msg and msg.get("msg") == "left":
            axes[0] = max(-1.0, axes[0] - 0.5)
        elif msg and msg.get("msg") == "right":
            axes[0] = min(1.0, axes[0] + 0.5)

        return FrameState(buttons=state.buttons, axes=tuple(axes), dpad=state.dpad)