# twitch_modifier.py
import asyncio
import json
import logging
import re
import threading
import time
from collections import deque
from enum import Enum, auto

import requests
import websockets

from XSerialOne.base import BaseModifier, FrameState
from XSerialOne.frame_constants import Axis, Button
from XSerialOne.macro_builder import MacroBuilder
from XSerialOne.macro_system import MacroManager

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

logger = logging.getLogger("twitch")
logging.basicConfig(level=logging.INFO)


# ============================================================
# EVENT SOURCE TYPES
# ============================================================

class EventSource(Enum):
    CHAT = auto()
    POINTS = auto()
    CHEER = auto()
    SUB = auto()


SOURCE_PRIORITY = {
    EventSource.SUB: 4,
    EventSource.CHEER: 3,
    EventSource.POINTS: 2,
    EventSource.CHAT: 1,
}


# ============================================================
# SHARED EVENT QUEUE
# ============================================================

class TwitchEventQueue:
    def __init__(self):
        self._queue = deque()
        self._lock = threading.Lock()

    def enqueue(self, msg: str, decay: float, source: EventSource):
        expire = time.time() + decay
        with self._lock:
            self._queue.append((expire, msg, source))

    def get_active(self):
        now = time.time()
        with self._lock:
            while self._queue and self._queue[0][0] < now:
                self._queue.popleft()
            return [(msg, source) for _, msg, source in self._queue]


# ============================================================
# TWITCH CHAT SERVER (IRC)
# ============================================================

class TwitchChatServer:
    def __init__(self, oauth_token: str, username: str, channel: str,
                 queue: TwitchEventQueue):
        self.oauth_token = oauth_token
        self.username = username
        self.channel = channel
        self.queue = queue

        self._thread = None
        self._stop_event = threading.Event()

        #self.HOLD_COMMANDS = {"inspect", "plant", "defuse", "prone"}
        self.HOLD_COMMANDS = {"plant", "defuse", "prone"}
        self.AXIS_PREFIXES = ("move", "walk", "strafe", "look", "aim", "turn", "shoot")

        self.PRESS_DECAY = 0.08
        self.HOLD_DECAY = 0.5

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)  # Wait max 2 seconds for thread to finish

    def _classify_message(self, msg: str):
        if msg.startswith("press "):
            return msg[6:], self.PRESS_DECAY

        if msg.startswith("hold "):
            return msg[5:], self.HOLD_DECAY

        for prefix in self.AXIS_PREFIXES:
            if msg.startswith(prefix):
                return msg, self.HOLD_DECAY

        if msg in self.HOLD_COMMANDS:
            return msg, self.HOLD_DECAY

        return msg, self.PRESS_DECAY

    def enqueue_message(self, msg: str):
        msg = msg.strip().lower()
        msg, decay = self._classify_message(msg)
        self.queue.enqueue(msg, decay, EventSource.CHAT)

    async def _main(self):
        reader, writer = await asyncio.open_connection("irc.chat.twitch.tv", 6667)
        writer.write(f"PASS {self.oauth_token}\r\n".encode())
        writer.write(f"NICK {self.username}\r\n".encode())
        writer.write(f"JOIN #{self.channel}\r\n".encode())
        await writer.drain()

        logger.info("Connected to Twitch IRC")

        try:
            while not self._stop_event.is_set():
                try:
                    # Use timeout to allow checking stop event periodically
                    data = await asyncio.wait_for(reader.readline(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                    
                if not data:
                    continue

                msg = data.decode(errors="ignore").strip()
                if msg.startswith("PING"):
                    writer.write(b"PONG :tmi.twitch.tv\r\n")
                    await writer.drain()
                    continue

                if "PRIVMSG" in msg:
                    user_msg = msg.split(":", 2)[-1]
                    self.enqueue_message(user_msg)
        finally:
            writer.close()
            await writer.wait_closed()

    def _run_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(self._main())
        try:
            loop.run_until_complete(task)
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Stopping Twitch thread...")
            self._stop_event.set()
            task.cancel()
            try:
                loop.run_until_complete(asyncio.wait_for(task, timeout=2.0))
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        finally:
            loop.close()


# ============================================================
# EVENTSUB LISTENER
# ============================================================

class EventSubListener:
    def __init__(self, oauth_token: str, client_id: str,
                 broadcaster_id: str, queue: TwitchEventQueue):
        self.oauth_token = oauth_token.replace("oauth:", "")
        self.client_id = client_id
        self.broadcaster_id = broadcaster_id
        self.queue = queue

        self._thread = None
        self._stop = threading.Event()

        self.REWARD_COMMANDS = {
            "Get Blooper'd!": ("flashbang", 0.1),
            "Spin Around": ("look 1 0", 2.0),
            "Become A Frog": ("jump_spam", 0.08),
            "Waste Ultimate": ("y", 0.1),
        }

    def start(self):
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)  # Wait max 2 seconds for thread to finish

    async def _subscribe(self, session_id: str):
        headers = {
            "Authorization": f"Bearer {self.oauth_token}",
            "Client-Id": self.client_id,
            "Content-Type": "application/json",
        }

        types = [
            "channel.channel_points_custom_reward_redemption.add",
            "channel.cheer",
            "channel.subscribe",
        ]

        for t in types:
            body = {
                "type": t,
                "version": "1",
                "condition": {"broadcaster_user_id": str(self.broadcaster_id)},
                "transport": {"method": "websocket", "session_id": session_id},
            }

            r = requests.post(
                "https://api.twitch.tv/helix/eventsub/subscriptions",
                headers=headers,
                json=body,
                timeout=10,
            )

            try:
                r.raise_for_status()
                logger.info(f"Subscribed to {t}")
            except requests.HTTPError:
                logger.error(f"Failed to subscribe {t}: {r.status_code} {r.text}")

    async def _handle_event(self, payload):
        event = payload["event"]
        etype = payload["subscription"]["type"]

        if etype == "channel.channel_points_custom_reward_redemption.add":
            print("Reward redeemed:", event)
            title = event["reward"]["title"]
            if title in self.REWARD_COMMANDS:
                cmd, decay = self.REWARD_COMMANDS[title]
                self.queue.enqueue(cmd, decay, EventSource.POINTS)

        elif etype == "channel.cheer":
            bits = event["bits"]
            if bits >= 100:
                self.queue.enqueue("hold shoot", 2.0, EventSource.CHEER)
            elif bits >= 10:
                self.queue.enqueue("shoot", 0.1, EventSource.CHEER)

        elif etype == "channel.subscribe":
            self.queue.enqueue("jump", 0.1, EventSource.SUB)

    async def _main(self):
        try:
            async with websockets.connect("wss://eventsub.wss.twitch.tv/ws") as ws:
                logger.info("Connected to EventSub")

                while not self._stop.is_set():
                    try:
                        # Use timeout to allow checking stop event periodically
                        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5.0))

                        mtype = msg["metadata"]["message_type"]
                        if mtype == "session_welcome":
                            session_id = msg["payload"]["session"]["id"]
                            await self._subscribe(session_id)

                        elif mtype == "notification":
                            await self._handle_event(msg["payload"])
                    except asyncio.TimeoutError:
                        continue
        except asyncio.CancelledError:
            logger.info("EventSub listener cancelled")
            raise

    def _run_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(self._main())
        try:
            loop.run_until_complete(task)
        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Stopping EventSub listener...")
            self._stop.set()
            task.cancel()
            try:
                loop.run_until_complete(asyncio.wait_for(task, timeout=2.0))
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        finally:
            loop.close()


# ============================================================
# INPUT MODIFIER
# ============================================================

class TwitchInputModifier(BaseModifier):
    # Rainbow Six Siege common commands
    #BUTTONS = {
    #    "jump": Button.A, "a": Button.A,
    #    "reload": Button.X, "x": Button.X, "defuse": Button.X, "plant": Button.X,
    #    "ult": Button.Y, "y": Button.Y, "inspect": Button.Y,
    #    "crouch": Button.B, "b": Button.B, "prone": Button.B,
    #    "lb": Button.LB, "leftbumper": Button.LB, "left bumper": Button.LB,
    #    "ls": Button.LS, "leftstick": Button.LS, "left stick": Button.LS,
    #    "rb": Button.RB, "rightbumper": Button.RB, "right bumper": Button.RB,
    #    "rs": Button.RS, "rightstick": Button.RS, "right stick": Button.RS,
    #}
    # Overwatch common commands
    BUTTONS = {
        "jump": Button.A, "a": Button.A,
        "reload": Button.X, "x": Button.X, "defuse": Button.X, "plant": Button.X,
        "crouch": Button.B, "b": Button.B, "prone": Button.B,
        "y": Button.Y,
        "lb": Button.LB, "leftbumper": Button.LB, "left bumper": Button.LB,
        "ls": Button.LS, "leftstick": Button.LS, "left stick": Button.LS,
        "rb": Button.RB, "rightbumper": Button.RB, "right bumper": Button.RB,
        "rs": Button.RS, "rightstick": Button.RS, "right stick": Button.RS,
    }
    AXES = {
        "left":  (0, -0.65),
        "right": (0,  0.65),
        "up":    (1, -0.65),
        "down":  (1,  0.65),
        "walk left":  (0, -0.65),
        "walk right": (0,  0.65),
        "walk up":    (1, -0.65),
        "walk down":  (1,  0.65),
        "move left":  (0, -0.65),
        "move right": (0,  0.65),
        "move up":    (1, -0.65),
        "move down":  (1,  0.65),
        "strafe left":  (0, -0.65),
        "strafe right": (0,  0.65),
        "strafe up":    (1, -0.65),
        "strafe down":  (1,  0.65),
        "walkleft":  (0, -0.65),
        "walkright": (0,  0.65),
        "walkup":    (1, -0.65),
        "walkdown":  (1,  0.65),
        "strafeleft":  (0, -0.65),
        "straferight": (0,  0.65),
        "strafeup":    (1, -0.65),
        "strafedown":  (1,  0.65),
        "moveleft":  (0, -0.65),
        "moveright": (0,  0.65),
        "moveup":    (1, -0.65),
        "movedown":  (1,  0.65),
        "forward":    (1, -0.65),
        "backward":  (1,  0.65),
        "walk left":  (0, -0.65),
        "walk right": (0,  0.65),
        "walk forward":    (1, -0.65),
        "walk backward":  (1,  0.65),
        "move forward":    (1, -0.65),
        "move back":  (1,  0.65),
        "move backward":  (1,  0.65),
        "strafe forward":    (1, -0.65),
        "strafe backward":  (1,  0.65),
        "walkforward":    (1, -0.65),
        "walkbackward":  (1,  0.65),
        "strafeforward":    (1, -0.65),
        "strafebackward":  (1,  0.65),
        "moveforward":    (1, -0.65),
        "movebackward":  (1,  0.65),
    }
    RIGHT_AXES = {
        "lookleft":  (2, -1.25),
        "lookright": (2,  1.25),
        "lookup":    (3, -0.65),
        "lookdown":  (3,  0.65),
        "look left":  (2, -0.5),
        "look right": (2,  1.25),
        "look up":    (3, -0.65),
        "look down":  (3,  0.65),
        "aimleft":  (2, -1.25),
        "aimright": (2,  1.25),
        "aimup":    (3, -0.65),
        "aimdown":  (3,  0.65),
        "aim left":  (2, -1.25),
        "aim right": (2,  1.25),
        "aim up":    (3, -0.65),
        "aim down":  (3,  0.65),
        "turnleft":  (2, -1.25),
        "turnright": (2,  1.25),
        "turnup":    (3, -0.65),
        "turndown":  (3,  0.65),
        "turn left":  (2, -1.25),
        "turn right": (2,  1.25),
        "turn up":    (3, -0.65),
        "turn down":  (3,  0.65),
    }
    TRIGGERS = {
        "shoot": Axis.RIGHTTRIGGER,
        "unshoot": Axis.RIGHTTRIGGER,
        "stopshoot": Axis.RIGHTTRIGGER,
        "stop shoot": Axis.RIGHTTRIGGER,
        "stop shooting": Axis.RIGHTTRIGGER,
        "rt": Axis.RIGHTTRIGGER,
        "aim": Axis.LEFTTRIGGER,
        "unaim": Axis.LEFTTRIGGER,
        "stopaim": Axis.LEFTTRIGGER,
        "stop aim": Axis.LEFTTRIGGER,
        "stop aiming": Axis.LEFTTRIGGER,
        "lt": Axis.LEFTTRIGGER,
    }

    def __init__(self, queue: TwitchEventQueue):
        super().__init__()
        self.queue = queue
        self.stick_override = None
        self.right_stick_override = None
        self.macro_manager = MacroManager()
        self.active_macros = set()
        self.macro_end_times = {}  # Track when macros should end
        
        # Pause system with keyboard hotkey
        self.is_paused = False
        self.pause_key = keyboard.Key.pause if HAS_PYNPUT else None
        self.listener = None
        if HAS_PYNPUT:
            self._start_keyboard_listener()

        # Define a full 2s jump spam macro: press A every 300ms (with loop=True)
        self.jump_spam_macro = (
            MacroBuilder("jump_spam")
            .press(Button.A).wait_ms(50).release(Button.A).wait_ms(250)
            .press(Button.B).wait_ms(50).release(Button.B).wait_ms(50)
            .press(Button.A).wait_ms(50).release(Button.A).wait_ms(50)
            .press(Button.B).wait_ms(50).release(Button.B).wait_ms(50)
            .build(loop=True)  # Enable looping so macro continues to run
        )

        self.macro_manager.register_macro(self.jump_spam_macro)

    def _start_keyboard_listener(self):
        """Start listening for pause key presses"""
        def on_press(key):
            try:
                if key == self.pause_key:
                    self.is_paused = not self.is_paused
                    print(f"\\n{'='*50}")
                    print(f"Twitch inputs: {'PAUSED' if self.is_paused else 'RESUMED'}")
                    print(f"{'='*50}\\n")
            except AttributeError:
                pass

        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.start()

    def stop_keyboard_listener(self):
        """Stop listening for keyboard input"""
        if self.listener:
            self.listener.stop()

    def _classify_message(self, msg: str):
        if msg.startswith("press "):
            return msg[6:], 0.08
        if msg.startswith("hold "):
            return msg[5:], 0.5
        if msg in {"inspect", "plant", "defuse", "prone"}:
            return msg, 0.5
        for prefix in ("move", "walk", "strafe", "look", "aim", "turn", "shoot"):
            if msg.startswith(prefix):
                return msg, 1.5
        return msg, 0.08

    def update(self, state: FrameState) -> FrameState:
        axes = list(state.axes)
        buttons = list(state.buttons)

        self.stick_override = None
        self.right_stick_override = None

        messages = self.queue.get_active()
        
        # Update macro timing - stop macros that have reached their end time
        current_time = time.perf_counter()
        for macro_name in list(self.active_macros):
            if macro_name in self.macro_end_times and current_time >= self.macro_end_times[macro_name]:
                self.macro_manager.stop(macro_name)
                self.active_macros.remove(macro_name)
                del self.macro_end_times[macro_name]

        # If paused, return neutral state (ignore all Twitch inputs)
        if self.is_paused:
            macro_state = self.macro_manager.update(current_time, state)
            return state

        if not messages:
            # Still need to update macros even if no messages
            macro_state = self.macro_manager.update(current_time, state)
            if macro_state is not state:
                return macro_state
            return state

        # Sort by EventSource priority (SUB > CHEER > POINTS > CHAT)
        messages.sort(key=lambda m: SOURCE_PRIORITY[m[1]], reverse=True)

        for msg, source in messages:
            if source == EventSource.POINTS and msg.lower() == "jump_spam":
                if "jump_spam" not in self.active_macros:
                    print("Activating jump spam macro from channel points!")
                    self.macro_manager.run("jump_spam")
                    self.active_macros.add("jump_spam")
                    # Stop macro after 2 seconds
                    self.macro_end_times["jump_spam"] = current_time + 10.0
            # Re-classify chat messages to apply press/hold logic
            if source == EventSource.CHAT:
                msg, _ = self._classify_message(msg)

            # Apply buttons
            if msg in self.BUTTONS:
                if msg == "y" and source == EventSource.CHAT:
                    continue
                else:
                    buttons[self.BUTTONS[msg]] = True

            # Apply triggers
            if msg in self.TRIGGERS:
                if msg[:2] == "un":
                    axes[self.TRIGGERS[msg]] = -1.0
                elif msg[:4] == "stop":
                    axes[self.TRIGGERS[msg]] = -1.0
                else:
                    axes[self.TRIGGERS[msg]] = 1.0

            # Apply axes
            if msg in self.AXES:
                idx, val = self.AXES[msg]
                axes[idx] = val

            if msg in self.RIGHT_AXES:
                idx, val = self.RIGHT_AXES[msg]
                axes[idx] = val

            if source == EventSource.POINTS:
                m = re.match(r"move ([\-0-9.]+) ([\-0-9.]+)", msg)
                if m:
                    lx = max(-1.0, min(1.0, float(m.group(1))))
                    ly = max(-1.0, min(1.0, float(m.group(2))))
                    self.stick_override = (lx, ly)
                m2 = re.match(r"look ([\-0-9.]+) ([\-0-9.]+)", msg)
                if m2:
                    rx = max(-1.0, min(1.0, float(m2.group(1))))
                    ry = max(-1.0, min(1.0, float(m2.group(2))))
                    self.right_stick_override = (rx, ry)

        
        # Clamp axes to [-1, 1]
        if self.stick_override:
            axes[0], axes[1] = self.stick_override

        if self.right_stick_override:
            axes[2], axes[3] = self.right_stick_override
        axes = [max(-1.0, min(1.0, a)) for a in axes]

        state = FrameState(buttons=tuple(buttons), axes=tuple(axes), dpad=state.dpad)

        # Update macros with current state
        macro_state = self.macro_manager.update(current_time, state)

        # If macros produced output, merge it with twitch buttons
        if macro_state is not state:  # Macro made changes
            merged_buttons = list(macro_state.buttons)
            merged_axes = list(macro_state.axes)
            
            # Twitch buttons can add to macro buttons (OR operation)
            for i, btn in enumerate(buttons):
                merged_buttons[i] = merged_buttons[i] or btn
            
            # For axes, macro has priority
            # (don't override axes that the macro is using)
            
            return FrameState(buttons=tuple(merged_buttons), axes=tuple(merged_axes), dpad=macro_state.dpad)
        
        return state


         
