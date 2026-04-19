"""
sequence.py
Author: Ellie V.

Simple sequence recording, playback, and storage for XSerialOne.

Provides JSON-serializable sequences of frame states with timing information.
Sequences can be recorded in real-time, edited, and played back without code.
"""

import json
import time
from dataclasses import dataclass
from typing import List, Optional

from XSerialOne.base import FrameState


@dataclass
class SequenceFrame:
    """A single frame in a sequence with timing information."""
    timestamp_ms: float  # Time since sequence start in milliseconds
    frame: dict  # FrameState as dict (buttons, axes, dpad)
    
    def to_dict(self) -> dict:
        return {
            "timestamp_ms": self.timestamp_ms,
            "frame": self.frame
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'SequenceFrame':
        return SequenceFrame(
            timestamp_ms=data["timestamp_ms"],
            frame=data["frame"]
        )


@dataclass
class Sequence:
    """Complete input sequence with metadata."""
    name: str
    description: str = ""
    frames: List[SequenceFrame] = None
    duration_ms: float = 0.0
    
    def __post_init__(self):
        if self.frames is None:
            self.frames = []
        if self.frames:
            self.duration_ms = self.frames[-1].timestamp_ms
    
    def add_frame(self, frame: FrameState, timestamp_ms: float):
        """Add a frame to the sequence."""
        self.frames.append(SequenceFrame(
            timestamp_ms=timestamp_ms,
            frame=frame.to_dict()
        ))
        self.duration_ms = timestamp_ms
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "duration_ms": self.duration_ms,
            "frames": [f.to_dict() for f in self.frames]
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'Sequence':
        seq = Sequence(
            name=data.get("name", ""),
            description=data.get("description", ""),
        )
        seq.frames = [SequenceFrame.from_dict(f) for f in data.get("frames", [])]
        seq.duration_ms = data.get("duration_ms", 0.0)
        return seq
    
    def save(self, filepath: str):
        """Save sequence to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @staticmethod
    def load(filepath: str) -> 'Sequence':
        """Load sequence from JSON file."""
        with open(filepath, 'r') as f:
            return Sequence.from_dict(json.load(f))
    
    def get_frame_at(self, elapsed_ms: float) -> Optional[FrameState]:
        """Get the frame state at a specific time in the sequence."""
        if not self.frames:
            return None
        
        # Find the frame at this time
        for i, seq_frame in enumerate(self.frames):
            if seq_frame.timestamp_ms >= elapsed_ms:
                return FrameState.from_dict(seq_frame.frame)
        
        # Return last frame if time is beyond sequence
        return FrameState.from_dict(self.frames[-1].frame)


class SequenceRecorder:
    """
    Records input frames in real-time with timestamps.
    
    Usage:
        recorder = SequenceRecorder("my_combo")
        recorder.start()
        # ... input happens ...
        sequence = recorder.stop()
        sequence.save("combo.json")
    """
    
    def __init__(self, name: str, description: str = ""):
        self.sequence = Sequence(name=name, description=description)
        self.start_time: Optional[float] = None
        self.recording = False
    
    def start(self):
        """Start recording."""
        self.sequence.frames = []
        self.start_time = time.time()
        self.recording = True
    
    def record_frame(self, frame: FrameState):
        """Record a single frame."""
        if not self.recording or self.start_time is None:
            return
        
        elapsed = (time.time() - self.start_time) * 1000.0  # Convert to ms
        self.sequence.add_frame(frame, elapsed)
    
    def stop(self) -> Sequence:
        """Stop recording and return the sequence."""
        self.recording = False
        return self.sequence
    
    def get_elapsed_ms(self) -> float:
        """Get elapsed time since recording started."""
        if not self.recording or self.start_time is None:
            return 0.0
        return (time.time() - self.start_time) * 1000.0
