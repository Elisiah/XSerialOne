from __future__ import annotations

import queue
import re
import threading
import time
from typing import Any, Dict

try:
    import pygame
except ImportError:
    pygame = None

from XSerialOne.base import FrameState


class TwitchDebugViewer:
    """
    Shows 'me' vs 'chat' side by side.
    """
    def __init__(self, left_tag: str = "me", right_tag: str = "chat", width: int = 800, height: int = 320):
        self.left_tag = left_tag
        self.right_tag = right_tag
        self.width = width
        self.height = height

        self._q: "queue.Queue" = queue.Queue()
        self._thread = None
        self._running = False
        self._latest = {self.left_tag: None, self.right_tag: None}

    def enqueue(self, tag: str, state: FrameState):
        """
        Enqueue a FrameState for a panel (either 'me' or 'chat')
        """
        try:
            self._q.put_nowait((tag, state.to_dict()))
        except Exception:
            pass

    def attach_to_pipeline(self, pipeline, twitch_server=None, decay_window=0.5):
        """
        Attach to your real input pipeline and optionally to Twitch server.
        """
        pipeline.add_generate_callback(lambda s: self.enqueue(self.left_tag, s))

        if twitch_server:
            # Spawn a watcher thread for twitch frames
            def twitch_watcher():
                last_active_time = 0.0

                while True:
                    messages = twitch_server.get_messages()

                    if messages:
                        last_active_time = time.time()

                        axes = [0.0]*6
                        buttons = [False]*15
                        dpad = (0,0,0,0)

                        for msg in messages:
                            m = msg.lower().strip()
                            if m == "jump": buttons[0] = True
                            if m == "shoot": axes[5] = 1.0
                            if m == "left": axes[0] = -1.0
                            if m == "right": axes[0] = 1.0
                            if m == "up": axes[1] = 1.0
                            if m == "down": axes[1] = -1.0

                            sm = re.match(r"stick ([\-0-9.]+) ([\-0-9.]+)", m)
                            if sm:
                                x = float(sm.group(1))
                                y = float(sm.group(2))

                                # Clamp
                                x = max(-1, min(1, x))
                                y = max(-1, min(1, y))

                                # Normalize to circle
                                mag = (x*x + y*y)**0.5
                                if mag > 1.0:
                                    x /= mag
                                    y /= mag

                                axes[0] = x
                                axes[1] = y

                        frame = FrameState(buttons=buttons, axes=tuple(axes), dpad=dpad)
                        self.enqueue(self.right_tag, frame)

                    else:
                        # no messages -> clear after decay window
                        if time.time() - last_active_time > decay_window:
                            neutral = FrameState(
                                buttons=[False]*15,
                                axes=(0.0,0.0,0.0,0.0,0.0,0.0),
                                dpad=(0,0,0,0)
                            )
                            self.enqueue(self.right_tag, neutral)

                    time.sleep(decay_window/2)


            threading.Thread(target=twitch_watcher, daemon=True).start()

    def start(self):
        if self._running:
            return
        if pygame is None:
            raise RuntimeError("pygame is required. Install with 'pip install pygame'")
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _drain_queue(self):
        while not self._q.empty():
            try:
                tag, sd = self._q.get_nowait()
                self._latest[tag] = sd
            except Exception:
                break

    def _run(self):
        pygame.init()
        screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Twitch vs Me Debug Viewer")
        clock = pygame.time.Clock()
        font = pygame.font.SysFont(None, 18)

        left_rect = pygame.Rect(10, 10, (self.width - 30) // 2, self.height - 20)
        right_rect = pygame.Rect(left_rect.right + 10, 10, left_rect.width, left_rect.height)

        while self._running:
            if pygame.key.get_pressed()[pygame.K_q]:
                self._running = False

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False

            self._drain_queue()
            screen.fill((16, 16, 16))

            self._draw_panel(screen, left_rect, font, self.left_tag, self._latest.get(self.left_tag))
            self._draw_panel(screen, right_rect, font, self.right_tag, self._latest.get(self.right_tag))

            pygame.display.flip()
            clock.tick(30)

        pygame.quit()

    def _draw_panel(self, surf, rect, font, title: str, sd: Dict[str, Any] | None):
        # Background panel
        pygame.draw.rect(surf, (28,28,28), rect, border_radius=12)
        title_s = font.render(title, True, (220,220,220))
        surf.blit(title_s, (rect.x+8, rect.y+6))

        if sd is None:
            surf.blit(font.render("<no data>", True, (180,180,180)), (rect.x+10, rect.y+40))
            return

        buttons = sd["buttons"]
        axes = sd["axes"]
        dpad = sd["dpad"]

        # -----------------------------
        # Positions (relative layout)
        # -----------------------------
        cx = rect.x + rect.w//2

        # Left stick
        LS_base = (rect.x+70, rect.y+120)

        # Right stick  (CHANGED → aligned with D-pad)
        RS_base = (rect.x+rect.w-70, rect.y+210)

        # ABXY cluster (CHANGED → aligned vertically with left stick)
        ABXY_center = (rect.x+rect.w-90, rect.y+120)

        # D-pad
        DP_center = (rect.x+70, rect.y+210)

        # Bumpers & triggers
        LB_pos = (rect.x+40, rect.y+35)
        RB_pos = (rect.x+rect.w-140, rect.y+35)
        LT_pos = (rect.x+40, rect.y+15)
        RT_pos = (rect.x+rect.w-140, rect.y+15)

        # Start/Back
        BACK_pos = (cx-30, rect.y+120)
        START_pos = (cx+30, rect.y+120)

        # -----------------------------
        # Helper drawing functions
        # -----------------------------
        def circ(pos, r, color):
            pygame.draw.circle(surf, color, pos, r)

        def rounded_rect(x, y, w, h, color):
            pygame.draw.rect(surf, color, (x,y,w,h), border_radius=6)

        # -----------------------------
        # Draw Bumpers (LB/RB)
        # -----------------------------
        LB_col = (100,255,100) if buttons[4] else (60,60,60)
        RB_col = (100,255,100) if buttons[5] else (60,60,60)
        rounded_rect(*LB_pos, 80, 18, LB_col)
        rounded_rect(*RB_pos, 80, 18, RB_col)

        # -----------------------------
        # Draw Triggers (LT / RT)
        # axes[4] = LT, axes[5] = RT typically
        # -----------------------------
        LT_val = max(0.0, min(1.0, axes[4]))
        RT_val = max(0.0, min(1.0, axes[5]))

        # Trigger bars fill based on axis
        pygame.draw.rect(surf, (40,40,40), (*LT_pos, 80, 12), border_radius=4)
        pygame.draw.rect(surf, (120,120,255), (*LT_pos, int(80*LT_val), 12), border_radius=4)

        pygame.draw.rect(surf, (40,40,40), (*RT_pos, 80, 12), border_radius=4)
        pygame.draw.rect(surf, (120,120,255), (*RT_pos, int(80*RT_val), 12), border_radius=4)

        # -----------------------------
        # Back / Start
        # -----------------------------
        BACK_col = (200,200,200) if buttons[6] else (70,70,70)
        START_col = (200,200,200) if buttons[7] else (70,70,70)
        circ(BACK_pos, 10, BACK_col)
        circ(START_pos, 10, START_col)

        # -----------------------------
        # ABXY Buttons
        # Buttons 0=A, 1=B, 2=X, 3=Y
        # -----------------------------
        A_pos = (ABXY_center[0],     ABXY_center[1] + 25)
        B_pos = (ABXY_center[0] +25, ABXY_center[1])
        X_pos = (ABXY_center[0] -25, ABXY_center[1])
        Y_pos = (ABXY_center[0],     ABXY_center[1] -25)

        A_col = (50,200,50) if buttons[0] else (20,90,20)
        B_col = (200,50,50) if buttons[1] else (90,20,20)
        X_col = (50,50,200) if buttons[2] else (20,20,90)
        Y_col = (200,200,50) if buttons[3] else (90,90,20)

        circ(A_pos, 14, A_col)
        circ(B_pos, 14, B_col)
        circ(X_pos, 14, X_col)
        circ(Y_pos, 14, Y_col)

        # Labels
        surf.blit(font.render("A", True, (255,255,255)), (A_pos[0]-4, A_pos[1]-6))
        surf.blit(font.render("B", True, (255,255,255)), (B_pos[0]-4, B_pos[1]-6))
        surf.blit(font.render("X", True, (255,255,255)), (X_pos[0]-4, X_pos[1]-6))
        surf.blit(font.render("Y", True, (255,255,255)), (Y_pos[0]-4, Y_pos[1]-6))

        # -----------------------------
        # D-Pad
        # -----------------------------
        # Directions: (up, right, down, left)
        # Ensure dpad is always a 4-tuple: (up, right, down, left)
        raw = dpad

        # Case 1: Already correct
        if len(raw) == 4:
            up, right, down, left_ = raw

        # Case 2: Gamepad-style (x,y)
        elif len(raw) == 2:
            x, y = raw
            up     = 1 if y > 0 else 0
            down   = 1 if y < 0 else 0
            right  = 1 if x > 0 else 0
            left_  = 1 if x < 0 else 0

        # Case 3: Unknown → neutral
        else:
            up = right = down = left_ = 0


        base = (40,40,40)
        active = (180,180,180)

        # Up
        pygame.draw.rect(
            surf, active if up else base,
            (DP_center[0]-12, DP_center[1]-30, 24, 22), border_radius=4
        )
        # Down
        pygame.draw.rect(
            surf, active if down else base,
            (DP_center[0]-12, DP_center[1]+8, 24, 22), border_radius=4
        )
        # Left
        pygame.draw.rect(
            surf, active if left_ else base,
            (DP_center[0]-30, DP_center[1]-12, 22, 24), border_radius=4
        )
        # Right
        pygame.draw.rect(
            surf, active if right else base,
            (DP_center[0]+8, DP_center[1]-12, 22, 24), border_radius=4
        )

        # -----------------------------
        # Joysticks (vector)
        # -----------------------------
        def draw_stick(base_pos, ax_idx, ay_idx, pressed_button=None):
            bx, by = base_pos
            outer_r = 28
            inner_r = 5     # CHANGED → half-size inner dot

            # Base circle
            circ((bx,by), outer_r, (50,50,50))
            pygame.draw.circle(surf, (90,90,90), (bx,by), outer_r, 2)

            # Stick position
            x = axes[ax_idx]
            y = axes[ay_idx]

            # clamp + normalize
            x = max(-1,min(1,x))
            y = max(-1,min(1,y))
            mag = (x*x + y*y)**0.5
            if mag > 1:
                x /= mag
                y /= mag

            sx = int(bx + x*(outer_r-10))
            sy = int(by + y*(outer_r-10))

            color = (100,255,100) if pressed_button else (180,180,180)
            circ((sx,sy), inner_r, color)

        # LS button = index 8, RS button = index 9
        draw_stick(LS_base, 0,1, pressed_button=buttons[8])
        draw_stick(RS_base, 2,3, pressed_button=buttons[9])

