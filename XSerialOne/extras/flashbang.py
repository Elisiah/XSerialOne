"""
flashbang.py
Author: Ellie V.

Blooper ink sploch overlay for Twitch channel points rewards.

This module provides a transparent Pygame window that splatters ink when
a blooper reward is redeemed via channel points, similar to the Blooper
effect from Mario Kart. The ink gradually drips off the screen over time.
"""

import random
import threading
import time
from typing import List, Optional

import pygame

from XSerialOne.extras.modules.twitch_chat import EventSource, TwitchEventQueue


class InkDroplet:
    """Single ink droplet that falls down the screen."""
    
    def __init__(self, x: float, y: float, size: float, fall_speed: float, start_time: float):
        self.x = x
        self.y = y
        self.size = size
        self.fall_speed = fall_speed  # pixels per second
        self.start_time = start_time
    
    def update(self, delta_time: float, current_time: float, animation_duration: float):
        """Update droplet position based on time in animation."""
        elapsed = current_time - self.start_time
        
        # After animation_duration, fall speed increases dramatically
        if elapsed > animation_duration:
            # Speed up to 500 px/sec to quickly fall off screen
            current_fall_speed = 500
        else:
            current_fall_speed = self.fall_speed
        
        self.y += current_fall_speed * delta_time
    
    def is_active(self, screen_height: int) -> bool:
        """Check if droplet is still on screen."""
        return self.y < screen_height


class FlashbangOverlay:
    """
    Ink sploch overlay (Blooper effect) that splatters on screen and drips off.
    Runs in a background thread and doesn't block main pipeline.
    """

    def __init__(
        self,
        queue: "TwitchEventQueue",
        reward_name: str = "Flashbang",
        animation_duration: float = 5.0,
        width: int = 1920,
        height: int = 1080,
        window_title: str = "Blooper Overlay",
    ):
        """
        Initialize the blooper overlay.

        Args:
            queue: TwitchEventQueue to monitor for rewards
            reward_name: Name of the channel points reward to trigger on
            animation_duration: How long the ink drips for (seconds)
            width: Window width in pixels
            height: Window height in pixels
            window_title: Title of the Pygame window
        """
        self.queue = queue
        self.reward_name = reward_name
        self.animation_duration = animation_duration
        self.width = width
        self.height = height
        self.window_title = window_title

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_splash_time = 0.0

    def start(self):
        """Start the blooper overlay in a background thread."""
        if self._thread and self._thread.is_alive():
            return
        print("[Blooper] Starting overlay...")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the blooper overlay."""
        print("[Blooper] Stopping overlay...")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _create_sploch(self, x: float, y: float, size: float, start_time: float) -> List[InkDroplet]:
        """Create a sploch of ink droplets at position."""
        droplets = []
        # Create a large splatter with many droplets
        num_droplets = 60
        for _ in range(num_droplets):
            # Random angle for splatter direction
            _angle = random.uniform(0, 2 * 3.14159)
            
            # Most droplets fall mostly downward, some go sideways
            _vel_x = random.uniform(-50, 50)  # Slight horizontal drift
            vel_y = random.uniform(10, 50)   # Slow downward drift (pixels/sec)
            
            drop_x = x + random.uniform(-150, 150)
            drop_y = y + random.uniform(-150, 150)
            drop_size = random.uniform(size * 0.5, size * 2.5)  # Much larger droplets
            
            droplets.append(InkDroplet(drop_x, drop_y, drop_size, vel_y, start_time))
        
        return droplets

    def _play_sploch_sound(self):
        """Play a sploch/ink sound effect."""
        try:
            import numpy as np
            
            # Initialize mixer if needed
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            
            sample_rate = 22050
            duration = 0.5  # 500ms sound
            num_samples = int(sample_rate * duration)
            
            # Create sound array using numpy
            t = np.linspace(0, duration, num_samples)
            
            # Single clean low frequency (100 Hz) for the plop/splat
            plop = np.sin(2 * np.pi * 100 * t) * 0.5
            
            # Apply sharp attack and exponential decay (plop envelope)
            decay = np.exp(-6 * t)
            
            # Combine - clean plop sound
            sound = plop * decay
            
            # Normalize and convert to 16-bit audio
            sound = np.int16(sound * 32767 * 0.7)
            
            # Create stereo by stacking left and right channels
            stereo = np.repeat(sound[:, np.newaxis], 2, axis=1).astype(np.int16)
            
            # Create sound object and play
            sound_obj = pygame.sndarray.make_sound(stereo)
            sound_obj.play()
            print("[Blooper] Plop sound played!")
            
        except ImportError:
            print("[Blooper] NumPy not available, skipping sound")
        except Exception as e:
            print(f"[Blooper] Could not play sound: {e}")
            # Continue without sound if it fails

    def _run_loop(self):
        """Main loop running in background thread."""
        pygame.init()
        pygame.display.init()

        # Create a regular windowed window
        screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(self.window_title)

        # Use bright green as chroma key (transparent in OBS)
        CHROMA_KEY = (0, 255, 0)
        INK_COLOR = (20, 20, 20)  # Dark ink
        
        # Start with transparent background
        screen.fill(CHROMA_KEY)
        pygame.display.update()

        clock = pygame.time.Clock()
        ink_droplets: List[InkDroplet] = []
        last_frame_time = time.perf_counter()

        print(f"[Blooper] Window opened: {self.width}x{self.height}")
        print(f"[Blooper] Listening for '{self.reward_name}' reward...")
        print(f"[Blooper] In OBS: Add 'Window Capture' source and select '{self.window_title}'")
        print("[Blooper] Then add a 'Color Key' filter with green color to make background transparent")

        try:
            while not self._stop_event.is_set():
                current_time = time.perf_counter()
                delta_time = min(current_time - last_frame_time, 0.033)  # Cap at ~30ms
                last_frame_time = current_time

                # Check for splash reward in queue
                messages = self.queue.get_active()
                for msg, source in messages:
                    if (
                        source == EventSource.POINTS
                        and msg.lower() == self.reward_name.lower()
                    ):
                        if current_time - self._last_splash_time > 0.5:  # Cooldown
                            _splash_active_time = current_time
                            self._last_splash_time = current_time
                            print(f"[Blooper] SPLOCH! ({self.reward_name} redeemed)")
                            
                            # Play sploch sound
                            self._play_sploch_sound()
                            
                            # Create sploches in a grid pattern to cover entire screen
                            cols = 3
                            rows = 2
                            col_width = self.width / cols
                            row_height = self.height / rows
                            
                            for row in range(rows):
                                for col in range(cols):
                                    # Add randomness within each grid cell
                                    x = col * col_width + random.uniform(col_width * 0.1, col_width * 0.9)
                                    y = row * row_height + random.uniform(row_height * 0.1, row_height * 0.5)
                                    new_droplets = self._create_sploch(x, y, 120, current_time)
                                    ink_droplets.extend(new_droplets)
                            
                            _splash_active_time = current_time  # Track when splash started

                # Update all droplets
                for droplet in ink_droplets[:]:
                    droplet.update(delta_time, current_time, self.animation_duration)
                    if not droplet.is_active(self.height):
                        ink_droplets.remove(droplet)

                # Clear to transparent (chroma key green)
                screen.fill(CHROMA_KEY)

                # Draw all active ink droplets as solid circles
                for droplet in ink_droplets:
                    # Draw solid ink blob (circle) directly to screen
                    pygame.draw.circle(
                        screen,
                        INK_COLOR,
                        (int(droplet.x), int(droplet.y)),
                        int(droplet.size),
                    )

                pygame.display.update()

                # Handle pygame events (window close, etc)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self._stop_event.set()

                clock.tick(60)  # 60 FPS for smooth animation

        except Exception as e:
            print(f"[Blooper] Error: {e}")
        finally:
            pygame.quit()
            print("[Blooper] Window closed")
