"""
example_input_detection.py
Author: Ellie V.

Example: Using the InputDetector for event-driven input handling.

Shows how to detect button presses, combos, double-taps, and other
input events without complex state machines.
"""

from XSerialOne.pipeline import InputPipeline
from XSerialOne.modules.xinput import XInputGenerator
from XSerialOne.input_detection import InputDetector
from XSerialOne.base import BaseModifier, FrameState
from XSerialOne.frame_constants import Button, Axis
import serial.tools.list_ports


class EventLoggingModifier(BaseModifier):
    """Modifier that logs input events to console."""
    
    def __init__(self, detector: InputDetector):
        super().__init__()
        self.detector = detector
    
    def update(self, state: FrameState) -> FrameState:
        self.detector.update(state)
        
        # Check for various events
        if self.detector.on_press(Button.A):
            print("✓ A pressed")
        
        if self.detector.on_release(Button.A):
            print("✗ A released")
        
        if self.detector.on_double_tap(Button.B, time_window_ms=300):
            print("⬥ B double-tapped!")
        
        if self.detector.on_combo([Button.X, Button.Y], time_window_ms=100):
            print("⌘ X+Y combo!")
        
        if self.detector.on_held(Button.LB, duration_ms=500):
            print("⏱ LB held for 500ms")
        
        if self.detector.on_stick_move((Axis.LEFTSTICKX, Axis.LEFTSTICKY), threshold=0.5):
            print("↗ Left stick moved significantly")
        
        if self.detector.on_trigger_pulled(Axis.RIGHTTRIGGER, threshold=0.2):
            print("→ Right trigger pulled")
        
        # Return the original state (this modifier is just logging)
        return state


class ComboResponderModifier(BaseModifier):
    """Modifier that responds to input combos by modifying output."""
    
    def __init__(self, detector: InputDetector):
        super().__init__()
        self.detector = detector
        self.combo_active = False
    
    def update(self, state: FrameState) -> FrameState:
        self.detector.update(state)
        
        # Detect combo: A + B
        if self.detector.on_combo([Button.A, Button.B]):
            self.combo_active = True
            print("→ Combo activated: A+B pressed")
        
        # When combo is active, boost stick sensitivity
        if self.combo_active:
            axes = list(state.axes)
            axes[Axis.LEFTSTICKX] *= 1.5  # 50% boost
            axes[Axis.LEFTSTICKY] *= 1.5
            
            # Deactivate when combo is released
            if not self.detector.is_pressed(Button.A) or not self.detector.is_pressed(Button.B):
                self.combo_active = False
                print("→ Combo deactivated")
            
            return FrameState(buttons=state.buttons, axes=tuple(axes), dpad=state.dpad)
        
        return state


def main():
    """Run the event detection example."""
    print("=== INPUT DETECTION EXAMPLE ===")
    print("Try these interactions:")
    print("  - Press A, B, X, Y buttons")
    print("  - Double-tap B quickly")
    print("  - Press X and Y together")
    print("  - Hold LB for 0.5 seconds")
    print("  - Move left stick")
    print("  - Pull right trigger")
    print("  - Press A+B together (combo)")
    print("\nPress Ctrl+C to exit.\n")
    
    # Setup pipeline
    xinput_gen = XInputGenerator()
    detector = InputDetector()
    
    event_logger = EventLoggingModifier(detector)
    combo_responder = ComboResponderModifier(detector)
    
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
    pipeline.add_modifier(event_logger)
    pipeline.add_modifier(combo_responder)
    
    try:
        pipeline.run_loop()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
