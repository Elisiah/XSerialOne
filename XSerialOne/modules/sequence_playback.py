"""
sequence_playback.py
Author: Ellie V.

Sequence playback module for XSerialOne.

Provides a generator that replays recorded input sequences with
configurable speed and looping behavior.
"""

import time

from XSerialOne.base import BaseGenerator, FrameState
from XSerialOne.sequence import Sequence


class SequencePlaybackGenerator(BaseGenerator):
    """
    Replays a recorded input sequence.
    
    Usage:
        seq = Sequence.load("combo.json")
        playback = SequencePlaybackGenerator(seq)
        playback.start()
        
        # In pipeline:
        pipeline.add_generator(playback)
        pipeline.run_loop()
    """
    
    def __init__(self, sequence: Sequence, speed: float = 1.0, loop: bool = False):
        """
        Initialize playback generator.
        
        Args:
            sequence: Sequence object to play back
            speed: Playback speed (1.0 = normal, 0.5 = half speed, 2.0 = double speed)
            loop: Whether to loop the sequence
        """
        super().__init__()
        self.sequence = sequence
        self.speed = speed
        self.loop = loop
        self.start_time: float = None
        self.is_playing = False
        self.current_frame_index = 0
    
    def start(self):
        """Start playback."""
        self.start_time = time.time()
        self.is_playing = True
        self.current_frame_index = 0
    
    def stop(self):
        """Stop playback."""
        self.is_playing = False
        self.start_time = None
        self.current_frame_index = 0
    
    def pause(self):
        """Pause playback (can be resumed with start())."""
        self.is_playing = False
    
    def resume(self):
        """Resume paused playback."""
        self.is_playing = True
        if self.start_time is None:
            self.start_time = time.time()
    
    def get_position_ms(self) -> float:
        """Get current playback position in milliseconds."""
        if not self.is_playing or self.start_time is None:
            return 0.0
        
        elapsed = (time.time() - self.start_time) * 1000.0
        return elapsed * self.speed
    
    def generate(self) -> FrameState:
        """Generate the current frame based on playback position."""
        if not self.is_playing or self.sequence is None or not self.sequence.frames:
            return FrameState()
        
        if self.start_time is None:
            self.start_time = time.time()
        
        elapsed_ms = self.get_position_ms()
        
        # Check if sequence is complete
        if elapsed_ms > self.sequence.duration_ms:
            if self.loop:
                # Restart sequence
                self.start_time = time.time()
                elapsed_ms = 0.0
            else:
                # Sequence finished
                self.is_playing = False
                return FrameState()
        
        # Find the appropriate frame
        if not self.sequence.frames:
            return FrameState()
        
        # Linear search for the frame at this timestamp
        # In future, could use binary search for large sequences
        current_frame = self.sequence.frames[0]
        
        for frame in self.sequence.frames:
            if frame.timestamp_ms <= elapsed_ms:
                current_frame = frame
            else:
                break
        
        return FrameState.from_dict(current_frame.frame)


class SequenceRecordingGenerator(BaseGenerator):
    """
    Records all input passing through to a sequence.
    
    Usage:
        recorder_gen = SequenceRecordingGenerator("my_inputs")
        physical_controller_gen = XInputGenerator()
        
        pipeline.add_generator(physical_controller_gen)
        # Add a pass-through generator that records
        pipeline.add_modifier(RecordingModifier(recorder_gen))
        
        # ... play game ...
        
        sequence = recorder_gen.get_sequence()
        sequence.save("recorded.json")
    """
    
    def __init__(self, name: str, description: str = ""):
        super().__init__()
        self.name = name
        self.description = description
        self.frames = []
        self.start_time = time.time()
        self.is_recording = False
    
    def start_recording(self):
        """Start recording."""
        self.frames = []
        self.start_time = time.time()
        self.is_recording = True
    
    def stop_recording(self) -> Sequence:
        """Stop recording and return the sequence."""
        self.is_recording = False
        
        seq = Sequence(name=self.name, description=self.description)
        seq.frames = self.frames
        if self.frames:
            seq.duration_ms = self.frames[-1].timestamp_ms
        
        return seq
    
    def record_frame(self, frame: FrameState):
        """Record a frame."""
        if not self.is_recording:
            return
        
        elapsed_ms = (time.time() - self.start_time) * 1000.0
        
        from XSerialOne.sequence import SequenceFrame
        self.frames.append(SequenceFrame(
            timestamp_ms=elapsed_ms,
            frame=frame.to_dict()
        ))
    
    def get_sequence(self) -> Sequence:
        """Get the current recorded sequence."""
        seq = Sequence(name=self.name, description=self.description)
        seq.frames = self.frames
        if self.frames:
            seq.duration_ms = self.frames[-1].timestamp_ms
        return seq
    
    def generate(self) -> FrameState:
        """Generator doesn't produce input, just records."""
        return FrameState()
