"""
example_sequence_builder.py
Author: Ellie V.

Examples of using SequenceBuilder to create sequences programmatically.

This shows the alternative to the GUI editor - building sequences in code
when you need templates, patterns, or procedural generation.
"""

from XSerialOne.sequence_builder import (
    SequenceBuilder,
    create_button_spam,
    create_stick_circle,
    create_stick_sine,
    load_and_modify,
)
from XSerialOne.sequence import Sequence
from XSerialOne.frame_constants import Button


def example_simple_combo():
    """Simple example: build a button combo programmatically."""
    print("1. SIMPLE COMBO")
    
    seq = (SequenceBuilder("double_jump")
        .press(Button.A, duration_ms=0)      # Press A immediately
        .wait(50)                             # Hold A for 50ms
        .release(Button.A, duration_ms=0)    # Release A
        .wait(30)                             # Wait 30ms
        .press(Button.B, duration_ms=0)      # Press B
        .wait(50)                             # Hold B for 50ms
        .release(Button.B, duration_ms=0)    # Release B
        .build())
    
    seq.save("double_jump_built.json")
    print(f"  Saved: {len(seq.frames)} frames, {seq.duration_ms:.0f}ms\n")


def example_button_spam():
    """Utility function: rapidly tap a button."""
    print("2. RAPID BUTTON SPAM")
    
    # Use utility function
    seq = create_button_spam(Button.A, presses=10, interval_ms=100)
    seq.save("button_spam.json")
    print(f"  Saved: {len(seq.frames)} frames, {seq.duration_ms:.0f}ms\n")


def example_combo_chain():
    """Chain multiple combos together."""
    print("3. COMBO CHAIN")
    
    seq = (SequenceBuilder("combo_chain", "X+A, then Y+B")
        # First combo: X+A
        .combo(Button.X, Button.A, interval_ms=50)
        .wait(100)
        # Second combo: Y+B
        .combo(Button.Y, Button.B, interval_ms=50)
        .wait(100)
        .build())
    
    seq.save("combo_chain.json")
    print(f"  Saved: {len(seq.frames)} frames, {seq.duration_ms:.0f}ms\n")


def example_stick_movement():
    """Analog stick movement patterns."""
    print("4. STICK MOVEMENT - CIRCLE")
    
    seq = create_stick_circle(radius=0.8, points=32)
    seq.save("stick_circle.json")
    print(f"  Saved: {len(seq.frames)} frames, {seq.duration_ms:.0f}ms\n")


def example_stick_sine():
    """Sine wave stick movement."""
    print("5. STICK MOVEMENT - SINE WAVE")
    
    seq = create_stick_sine(amplitude=1.0, cycles=3, points_per_cycle=20)
    seq.save("stick_sine.json")
    print(f"  Saved: {len(seq.frames)} frames, {seq.duration_ms:.0f}ms\n")


def example_complex_sequence():
    """More complex sequence with mixed inputs."""
    print("6. COMPLEX SEQUENCE")
    
    seq = (SequenceBuilder("complex", "Move stick, press buttons, trigger")
        # Start with stick movement
        .stick("right", 0.5, 0.5, duration_ms=100)
        .stick("right", 0.0, 0.0, duration_ms=50)
        
        # Then some button combo
        .press(Button.X, duration_ms=50)
        .wait(30)
        .press(Button.Y, duration_ms=50)
        .wait(30)
        
        # Then trigger
        .trigger("right", 0.8, duration_ms=100)
        .wait(50)
        
        # Mix stick + button
        .frame(buttons=[Button.A], 
               stick_left=(0.7, 0.3),
               duration_ms=100)
        
        .build())
    
    seq.save("complex_sequence.json")
    print(f"  Saved: {len(seq.frames)} frames, {seq.duration_ms:.0f}ms\n")


def example_template_variations():
    """Create multiple variations from a template."""
    print("7. TEMPLATE VARIATIONS")
    
    # Create a template function
    def tap_pattern(name: str, buttons, intervals):
        """Create a pattern of button taps."""
        seq = SequenceBuilder(name)
        for btn, interval in zip(buttons, intervals):
            seq.press(btn, duration_ms=50).wait(interval - 50)
        return seq.build()
    
    # Use it to create variations
    easy = tap_pattern("tap_easy", [Button.A, Button.B, Button.A], [200, 200, 200])
    hard = tap_pattern("tap_hard", [Button.A, Button.B, Button.A, Button.X], [100, 100, 100, 100])
    
    easy.save("tap_easy.json")
    hard.save("tap_hard.json")
    
    print(f"  Easy: {len(easy.frames)} frames, {easy.duration_ms:.0f}ms")
    print(f"  Hard: {len(hard.frames)} frames, {hard.duration_ms:.0f}ms\n")


def example_load_and_modify():
    """Load an existing sequence and modify it."""
    print("8. LOAD AND MODIFY")
    
    # First create one
    original = (SequenceBuilder("original")
        .press(Button.A, duration_ms=50)
        .wait(100)
        .press(Button.B, duration_ms=50)
        .wait(100)
        .build())
    
    original.save("original.json")
    print(f"  Original: {original.duration_ms:.0f}ms")
    
    # Now load and slow it down
    slower = load_and_modify("original.json", speed_factor=0.5)
    slower.name = "original_slow"
    slower.save("original_slow.json")
    print(f"  Slowed to 50%: {slower.duration_ms:.0f}ms")
    
    # Speed it up
    faster = load_and_modify("original.json", speed_factor=1.5)
    faster.name = "original_fast"
    faster.save("original_fast.json")
    print(f"  Sped up to 150%: {faster.duration_ms:.0f}ms\n")


def example_double_tap():
    """Double-tap detection training sequence."""
    print("9. DOUBLE-TAP")
    
    seq = (SequenceBuilder("double_tap_train", "Training for double-tap timing")
        .double_tap(Button.A, interval_ms=200)
        .wait(200)
        .double_tap(Button.B, interval_ms=250)
        .wait(200)
        .double_tap(Button.X, interval_ms=300)
        .build())
    
    seq.save("double_tap.json")
    print(f"  Saved: {len(seq.frames)} frames, {seq.duration_ms:.0f}ms\n")


def example_hold_buttons():
    """Holding buttons for specific durations."""
    print("10. HOLD BUTTONS")
    
    seq = (SequenceBuilder("hold_test")
        .hold(Button.LB, 500)    # Hold 500ms
        .wait(200)
        .hold(Button.RB, 1000)   # Hold 1000ms
        .wait(200)
        .hold(Button.LT, 300)    # Actually triggers (LT axis)
        .build())
    
    seq.save("hold.json")
    print(f"  Saved: {len(seq.frames)} frames, {seq.duration_ms:.0f}ms\n")


def main():
    """Run all examples."""
    print("\n=== SEQUENCE BUILDER EXAMPLES ===\n")
    
    example_simple_combo()
    example_button_spam()
    example_combo_chain()
    example_stick_movement()
    example_stick_sine()
    example_complex_sequence()
    example_template_variations()
    example_load_and_modify()
    example_double_tap()
    example_hold_buttons()
    
    print("\n=== COMPARISON WITH GUI ===\n")
    
    print("GUI Editor (launch_macro_editor.py):")
    print("  ✓ Visual, click-and-drag")
    print("  ✓ Good for one-off sequences")
    print("  ✓ Shareable with non-programmers")
    print("  ✗ Hard to create patterns")
    print("  ✗ No version control friendly")
    print()
    
    print("SequenceBuilder (this file):")
    print("  ✓ Programmatic, revision control friendly")
    print("  ✓ Great for patterns and templates")
    print("  ✓ Easy to batch create variations")
    print("  ✗ Requires Python knowledge")
    print("  ✗ More typing than GUI")
    print()
    
    print("Input Recording (example_sequence_recording.py):")
    print("  ✓ Records real player input")
    print("  ✓ No building needed, just play")
    print("  ✓ Most authentic sequences")
    print("  ✗ Can't create artificial patterns")
    print()
    
    print("All three methods produce the same JSON format - mix and match!")
    print("\nSequences saved to:  *.json files")


if __name__ == "__main__":
    main()
