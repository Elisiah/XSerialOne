import asyncio
import copy
import json
import logging
import math
import threading
from typing import Any, Dict, Optional

import websockets

from XSerialOne.base import BaseModifier, FrameState

logger = logging.getLogger("relay")
logging.basicConfig(level=logging.INFO)


class RelayServer:
    """
    WebSocket server that receives remote XInput frames.
    Provides lock-free access to the latest frame.
    """
    def __init__(self, ws_port: int = 8765):
        self.ws_port = ws_port
        self._latest_frame: Optional[Dict[str, Any]] = None
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event = asyncio.Event()

    async def _handler(self, websocket):
        try:
            async for msg in websocket:
                try:
                    obj = json.loads(msg)
                    if obj.get("type") == "xinput_state":
                        self._latest_frame = copy.deepcopy(obj)

                except json.JSONDecodeError:
                    continue
        except websockets.ConnectionClosed:
            logger.info("Remote client disconnected")

    async def _start_server(self):
        async with websockets.serve(self._handler, "127.0.0.1", self.ws_port):
            logger.info(f"Relay listening on ws://127.0.0.1:{self.ws_port}")
            await self._stop_event.wait()

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._start_server())

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        if self._loop:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread:
            self._thread.join()

    def get_latest(self) -> Optional[Dict[str, Any]]:
        """
        Return latest frame lock-free.
        Important: frame MUST NOT be mutated by receiver.
        """
        return self._latest_frame



class MergeRemoteModifier(BaseModifier):
    """
    Modifier that merges local controller input with the latest remote frame.
    Axes are averaged, triggers take max, buttons/dpad ORed.
    """
    def __init__(self, relay_server: RelayServer):
        super().__init__()
        self.relay_server = relay_server

    def _normalize_stick(self, value: int, scale: float = 32768.0) -> float:
        """Normalize a stick axis value to [-1.0, 1.0]."""
        try:
            return max(-1.0, min(1.0, float(value) / scale))
        except (TypeError, ValueError):
            return 0.0

    def _normalize_trigger(self, value: float) -> float:
        return (value * 2.0) - 1.0

    def merge_stick(self, lx, ly, rx, ry):
        # Local and remote stick magnitudes
        mag_l = math.hypot(lx, ly)
        mag_r = math.hypot(rx, ry)

        # Case 1: both sticks neutral
        if mag_l == 0 and mag_r == 0:
            return 0.0, 0.0

        # Case 2: one stick neutral: take the one that moved
        if mag_l == 0:
            return rx, ry
        if mag_r == 0:
            return lx, ly

        # Case 3: both moving: vector average, weighted by magnitude
        mx = (lx * mag_l + rx * mag_r) / (mag_l + mag_r)
        my = (ly * mag_l + ry * mag_r) / (mag_l + mag_r)

        # Clamp final magnitude to 1.0 if it slightly exceeds due to rounding
        final_mag = math.hypot(mx, my)
        if final_mag > 1.0:
            mx /= final_mag
            my /= final_mag

        return mx, my


    def update(self, state: FrameState) -> FrameState:
        remote = self.relay_server.get_latest()
        if not remote:
            return state

        raw = remote["state"]["axes"]

        # === REAL NORMALIZATION (sticks left alone, triggers converted) ===
        remote_axes = [
            raw[0], raw[1], raw[2], raw[3],             # sticks already in [-1,1]
            self._normalize_trigger(raw[4]),            # LT: 0→-1, 1→1
            self._normalize_trigger(raw[5])             # RT
        ]

        # === Stick merging using your merge_stick() ===
        # Left stick (0–1)
        m0, m1 = self.merge_stick(
            state.axes[0], state.axes[1],
            remote_axes[0], remote_axes[1]
        )

        # Right stick (2–3)
        m2, m3 = self.merge_stick(
            state.axes[2], state.axes[3],
            remote_axes[2], remote_axes[3]
        )

        # Triggers (axes 4–5)
        local_trigs = state.axes[4:6]
        remote_trigs = remote_axes[4:6]
        merged_trigs = [
            max(local_trigs[0], remote_trigs[0]),
            max(local_trigs[1], remote_trigs[1])
        ]

        # Combine all axes into one list
        axes = [m0, m1, m2, m3] + merged_trigs

        # Buttons OR
        buttons = [l or r for l, r in zip(state.buttons, remote["state"]["buttons"])]

        # Dpad OR
        dpad = tuple(max(l, r) for l, r in zip(state.dpad, remote["state"]["dpad"]))

        return FrameState(buttons=buttons, axes=tuple(axes), dpad=dpad)




