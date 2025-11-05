"""
debug_viewer.py
Author: Ellie V.

Real-time visual debugging tool for the XSerialOne framework.

This module provides a graphical interface for monitoring controller state
in real-time, showing side-by-side comparisons of input states before
and after modification. Uses Pygame to render an interactive visualization
of controller inputs including buttons, analog sticks, and triggers.
"""

#TODO: Improve Visual Layout

from __future__ import annotations
import threading
import queue
import time
from typing import Dict, Any

try:
    import pygame
except Exception:
    pygame = None

from XSerialOne.base import FrameState


class DebugViewer:
    def __init__(self, left_tag: str = "gen", show_second_screen = False, right_tag: str = "post", width: int = 800, height: int = 320):
        self.left_tag = left_tag
        self.show_second_screen = show_second_screen
        self.right_tag = right_tag
        self._q: "queue.Queue" = queue.Queue()
        self._thread = None
        self._running = False
        self.width = width
        self.height = height

        self._latest = {self.left_tag: None, self.right_tag: None}

    def enqueue(self, tag: str, state: FrameState):
        try:
            self._q.put_nowait((tag, state.to_dict()))
        except Exception:
            pass

    def attach_to_pipeline(self, pipeline):
        pipeline.add_generate_callback(lambda s: self.enqueue(self.left_tag, s))
        pipeline.add_post_mod_callback(lambda s: self.enqueue(self.right_tag, s))

    def start(self):
        if self._running:
            return
        if pygame is None:
            raise RuntimeError("pygame is required for PygameDebugViewer. Install it with 'pip install pygame'.")
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
        pygame.display.set_caption("XSerialOne Debug Viewer")
        clock = pygame.time.Clock()
        font = pygame.font.SysFont(None, 18)

        left_rect = pygame.Rect(10, 10, (self.width - 30) // 2, self.height - 20)
        if self.show_second_screen:
            right_rect = pygame.Rect(left_rect.right + 10, 10, left_rect.width, left_rect.height)

        while self._running:
            # quit on q pressed 

            if pygame.key.get_pressed()[pygame.K_q]:
                self._running = False
                
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False

            self._drain_queue()

            screen.fill((16, 16, 16))

            self._draw_panel(screen, left_rect, font, self.left_tag, self._latest.get(self.left_tag))

            if self.show_second_screen:
                self._draw_panel(screen, right_rect, font, self.right_tag, self._latest.get(self.right_tag))

            pygame.display.flip()
            clock.tick(30)

        pygame.quit()

    def _draw_panel(self, surf, rect, font, title: str, sd: Dict[str, Any] | None):
        # background
        pygame.draw.rect(surf, (28, 28, 28), rect)
        # title
        title_s = font.render(title, True, (220, 220, 220))
        surf.blit(title_s, (rect.x + 6, rect.y + 6))

        inner_x = rect.x + 8
        inner_y = rect.y + 30

        if sd is None:
            txt = font.render("<no data>", True, (180, 180, 180))
            surf.blit(txt, (inner_x, inner_y))
            return

        # Buttons: 2 rows x 5 cols
        btn_w = 32
        btn_h = 20
        gap = 8
        buttons = sd.get("buttons", [])
        # Labels for buttons (indices 0..9)
        BUTTON_LABELS = ["A", "B", "X", "Y", "LB", "RB", "BACK", "START", "LS", "RS"]
        # Per-button color (pressed, unpressed)
        COLOR_MAP = {
            0: ((0, 200, 0), (60, 60, 60)),   # A green
            1: ((220, 40, 40), (60, 60, 60)), # B red
            2: ((40, 120, 220), (60, 60, 60)),# X blue
            3: ((220, 200, 40), (60, 60, 60)),# Y yellow
        }
        for row in range(2):
            for col in range(5):
                i = row * 5 + col
                x = inner_x + col * (btn_w + gap)
                y = inner_y + row * (btn_h + gap)
                pressed = False
                if i < len(buttons):
                    pressed = bool(buttons[i])
                if i in COLOR_MAP:
                    pressed_color, unpressed_color = COLOR_MAP[i]
                else:
                    pressed_color, unpressed_color = (0, 180, 180), (70, 70, 70)
                color = pressed_color if pressed else unpressed_color
                pygame.draw.rect(surf, color, (x, y, btn_w, btn_h), border_radius=4)

                # Draw label centered on the button
                label = BUTTON_LABELS[i] if i < len(BUTTON_LABELS) else str(i)
                lbl_surf = font.render(label, True, (255, 255, 255) if pressed else (220, 220, 220))
                lw, lh = lbl_surf.get_size()
                lx = x + (btn_w - lw) // 2
                ly = y + (btn_h - lh) // 2
                surf.blit(lbl_surf, (lx, ly))

        # Draw analog sticks (left: axes 0,1), (right: axes 2,3)
        axes = sd.get("axes", [])
        js_size = min(140, rect.width // 3)
        axes_y = inner_y + 2 * (btn_h + gap) + 12

        left_box_x = inner_x
        left_box_y = axes_y
        right_box_x = inner_x + js_size + 12
        right_box_y = axes_y

        def _get_axis(i):
            try:
                return float(axes[i]) if i < len(axes) else 0.0
            except Exception:
                return 0.0

        # Draw each stick box and position marker
        for box_x, box_y, ax_idx, ay_idx in (
            (left_box_x, left_box_y, 0, 1),
            (right_box_x, right_box_y, 2, 3),
        ):
            cx = box_x + js_size // 2
            cy = box_y + js_size // 2
            radius = js_size // 2 - 8
            # box
            pygame.draw.rect(surf, (40, 40, 40), (box_x, box_y, js_size, js_size), border_radius=8)
            # neutral circle
            pygame.draw.circle(surf, (80, 80, 80), (cx, cy), radius, 2)

            vx = _get_axis(ax_idx)
            vy = _get_axis(ay_idx)
            # clamp
            if vx < -1.0: vx = -1.0
            if vx > 1.0: vx = 1.0
            if vy < -1.0: vy = -1.0
            if vy > 1.0: vy = 1.0

            # map to pixel coords (invert Y so -1 is up)
            px = int(cx + vx * (radius - 4))
            py = int(cy + vy * (radius - 4))

            # draw position marker
            pygame.draw.circle(surf, (200, 200, 80), (px, py), 8)

            # small text with values
            txt = font.render(f"{vx:+.2f},{vy:+.2f}", True, (200, 200, 200))
            surf.blit(txt, (box_x, box_y + js_size + 4))

        # Remaining axes (triggers) as bars: axes[4]=LT, axes[5]=RT
        trig_y = axes_y + js_size + 28
        bar_w = rect.width - 24
        bar_h = 14
        for i, label in ((4, "LT"), (5, "RT")):
            v = _get_axis(i)
            # convert trigger range -1..1 to 0..1 (if triggers use -1..1)
            # assume 0..1 or -1..1; map both to 0..1
            normalized = (v + 1.0) / 2.0
            normalized = max(0.0, min(1.0, normalized))
            w = int(normalized * bar_w)
            y = trig_y + (i - 4) * (bar_h + 6)
            pygame.draw.rect(surf, (60, 60, 60), (inner_x, y, bar_w, bar_h), 1)
            pygame.draw.rect(surf, (220, 80, 80), (inner_x + 1, y + 1, max(0, w - 2), bar_h - 2))
            val_s = font.render(f"{label} {v:+.2f}", True, (220, 220, 220))
            surf.blit(val_s, (inner_x + bar_w + 6, y))

        # DPad
        dpad = sd.get("dpad", (0, 0))
        d_s = font.render(f"DPad: {tuple(dpad)}", True, (200, 200, 200))
        # move the dpad text further down toward the bottom of the panel
        surf.blit(d_s, (inner_x, rect.bottom - 12))
