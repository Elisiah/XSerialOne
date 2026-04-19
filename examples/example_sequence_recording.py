"""
example_sequence_recording.py
Author: Ellie V.

Example: Recording an input sequence and playing it back.

This demonstrates the simplified sequence recording/playback approach
as an alternative to the complex macro system.
"""

from XSerialOne.pipeline import InputPipeline
from XSerialOne.modules.xinput import XInputGenerator
from XSerialOne.modules.sequence_playback import SequencePlaybackGenerator
from XSerialOne.input_detection import InputDetector
from XSerialOne.sequence import Sequence, SequenceRecorder
from XSerialOne.base import BaseModifier, FrameState
from XSerialOne.frame_constants import Button
import serial.tools.list_ports


class SequenceRecordingModifier(BaseModifier):
    """Modifier that records input with keyboard hotkey control.
    
    R key: Enable/disable recording
    SPACE: Stop recording and trim trailing silence
    """
    
    def __init__(self, recorder: SequenceRecorder):
        super().__init__()
        self.recorder = recorder
        self.init_frame = None
        self.started = False
        self.recording_enabled = False
        self.recording_completed = False  # Track if recording finished with SPACE
    
    def check_keyboard(self):
        """Non-blocking keyboard check (Windows)."""
        try:
            import msvcrt
            if msvcrt.kbhit():
                key = msvcrt.getch().lower()
                if key == b'r':
                    self.recording_enabled = not self.recording_enabled
                    status = 'ENABLED' if self.recording_enabled else 'DISABLED'
                    print(f"\n>> Recording: {status}")
                    return True
                elif key == b' ':
                    if self.started:
                        self.started = False
                        self.recording_enabled = False  # Disable to prevent auto-restart
                        self.recording_completed = True  # Mark that recording was completed
                        print("\n>> Recording stopped.")
                        return True
        except:
            pass
        return False
    
    def has_meaningful_input(self, state: FrameState, init_frame: FrameState) -> bool:
        """Check if state has meaningful input (button/trigger changes, ignoring stick drift)."""
        # Compare buttons
        if state.buttons != init_frame.buttons:
            return True
        
        # Compare triggers (threshold 0.1 to ignore drift)
        if abs(state.axes[4] - init_frame.axes[4]) > 0.1:  # Left trigger
            return True
        if abs(state.axes[5] - init_frame.axes[5]) > 0.1:  # Right trigger
            return True
        
        # Ignore stick drift - don't compare sticks
        return False
    
    def update(self, state: FrameState) -> FrameState:
        # Capture initial frame on first update
        if self.init_frame is None:
            self.init_frame = state
            print("Initial state captured. Press 'R' to enable recording.")
        
        # Check keyboard input
        self.check_keyboard()
        
        # Wait for recording to be enabled by hotkey
        if not self.recording_enabled:
            return state
        
        # Wait for first input different from initial frame (buttons/triggers only, ignore stick drift)
        if not self.started:
            if self.has_meaningful_input(state, self.init_frame):
                self.recorder.start()
                self.started = True
                print("First input detected - recording started!")
        
        # Record if started
        if self.started:
            self.recorder.record_frame(state)
        
        return state


def trim_trailing_neutral_frames(sequence: Sequence, init_frame: FrameState):
    """Remove leading and trailing frames that are the same as the initial frame."""
    if not sequence.frames:
        return
    
    init_dict = init_frame.to_dict()
    
    # Find first active frame (different from init)
    first_active_idx = 0
    for i, frame in enumerate(sequence.frames):
        if frame.frame != init_dict:
            first_active_idx = i
            break
    
    # Find last active frame (different from init)
    last_active_idx = first_active_idx
    for i, frame in enumerate(sequence.frames):
        if frame.frame != init_dict:
            last_active_idx = i
    
    # Keep only frames from first active to last active
    sequence.frames = sequence.frames[first_active_idx:last_active_idx + 1]
    
    # Adjust timestamps to start from 0
    if sequence.frames:
        start_time = sequence.frames[0].timestamp_ms
        for frame in sequence.frames:
            frame.timestamp_ms -= start_time
        sequence.duration_ms = sequence.frames[-1].timestamp_ms


def main_record_combo():
    """Example 1: Record a button combo sequence."""
    print("=== RECORDING MODE ===")
    print("Hold down a button combo and release. Recording will happen in real-time.")
    
    # Create recorder
    recorder = SequenceRecorder("Double Jump Combo", description="A+B double jump in Binding of Isaac")
    
    # Setup pipeline
    xinput_gen = XInputGenerator()
    recording_mod = SequenceRecordingModifier(recorder)
    
    ports = [p.device for p in serial.tools.list_ports.comports()]
    
    if ports:
        print("\nAvailable COM ports:")
        for i, port in enumerate(ports):
            print(f"  {i}: {port}")
        try:
            port_idx = int(input("Select port number: "))
            com_port = ports[port_idx]
        except (ValueError, IndexError):
            print("Invalid selection, using first available port.")
            com_port = ports[0]
        pipeline = InputPipeline(com_port)
    else:
        print("No COM ports found, running without hardware")
        pipeline = InputPipeline()
    
    pipeline.add_generator(xinput_gen)
    pipeline.add_modifier(recording_mod)
    
    # Instructions for user
    print("\nControls:")
    print("  'R' - Enable/disable recording")
    print("  'SPACE' - Stop recording and save")
    print("\nPress Ctrl+C to exit.\n")
    
    try:
        pipeline.run_loop()
    except KeyboardInterrupt:
        pass
    finally:
        # Check if recording was completed via SPACE or if still active on Ctrl+C
        if recording_mod.recording_completed or recording_mod.started:
            # Trim trailing neutral frames before saving
            sequence = recording_mod.recorder.stop()
            trim_trailing_neutral_frames(sequence, recording_mod.init_frame)
            sequence.save("double_jump.json")
            print(f"Sequence saved to double_jump.json ({sequence.duration_ms:.0f}ms, {len(sequence.frames)} frames)")
        else:
            print("No recording was made.")


def main_playback_combo():
    """Example 2: Playback a recorded combo on button press."""
    print("=== PLAYBACK MODE ===")
    print("Press X button to trigger the recorded sequence.")
    
    # Load the sequence
    sequence = Sequence.load("double_jump.json")
    print(f"Loaded sequence: {sequence.name} ({len(sequence.frames)} frames)")
    
    # Setup pipeline with COM port selection
    ports = [p.device for p in serial.tools.list_ports.comports()]
    
    if ports:
        print("\nAvailable COM ports:")
        for i, port in enumerate(ports):
            print(f"  {i}: {port}")
        try:
            port_idx = int(input("Select port number: "))
            com_port = ports[port_idx]
        except (ValueError, IndexError):
            print("Invalid selection, using first available port.")
            com_port = ports[0]
        pipeline = InputPipeline(com_port)
    else:
        print("No COM ports found, running without hardware")
        pipeline = InputPipeline()
    
    # Create playback generator and detector
    xinput_gen = XInputGenerator()
    detector = InputDetector()
    playback = SequencePlaybackGenerator(sequence, speed=1.0, loop=False)
    
    # Modifier that triggers playback on button press
    class ComboTriggerModifier(BaseModifier):
        def __init__(self, det: InputDetector, pb: SequencePlaybackGenerator):
            super().__init__()
            self.detector = det
            self.playback = pb
            self.triggered_this_frame = False
        
        def update(self, state: FrameState) -> FrameState:
            self.detector.update(state)
            
            # Trigger playback on X button press
            if self.detector.on_press(Button.X) and not self.triggered_this_frame:
                self.playback.start()
                self.triggered_this_frame = True
                print("Combo triggered!")
                # Return first frame immediately
                return self.playback.generate()
            
            # Reset trigger flag when button is released
            if self.detector.on_release(Button.X):
                self.triggered_this_frame = False
            
            # If playback is active, use playback output
            if self.playback.is_playing:
                return self.playback.generate()
            else:
                return state
    
    pipeline.add_generator(xinput_gen)
    pipeline.add_modifier(ComboTriggerModifier(detector, playback))
    
    print("Press X to trigger combo. Ctrl+C to stop.")
    try:
        pipeline.run_loop()
    except KeyboardInterrupt:
        print("\nStopped.")


def main_blend_inputs():
    """Example 3: Blend vision aiming with hand tracking."""
    print("=== BLENDED INPUT EXAMPLE ===")
    print("This shows how to combine multiple input sources.")
    
    # This is pseudo-code showing the concept:
    # 
    # from XSerialOne.modules.hand_tracking import HandTrackingGenerator
    # from XSerialOne.modules.vision_aiming import VisionAimbotModifier
    #
    # pipeline = InputPipeline()
    # pipeline.add_generator(XInputGenerator())  # Physical controller
    # pipeline.add_generator(HandTrackingGenerator())  # Hand-based input
    # pipeline.add_modifier(DeadzoneModifier())
    # pipeline.add_modifier(VisionAimbotModifier())  # Vision assist
    # pipeline.add_modifier(SmoothingModifier())
    
    print("See the Portfolio article for vision+gesture integration examples.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "record":
            main_record_combo()
        elif mode == "playback":
            main_playback_combo()
        elif mode == "blend":
            main_blend_inputs()
        else:
            print("Usage: python example_sequence_recording.py [record|playback|blend]")
    else:
        print("Choose mode:")
        print("  1. Record combo: python example_sequence_recording.py record")
        print("  2. Playback combo: python example_sequence_recording.py playback")
        print("  3. Blend inputs: python example_sequence_recording.py blend")
