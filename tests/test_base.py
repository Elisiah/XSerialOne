"""Tests for base.py classes and utilities."""
import conftest

def test_base_generator_default_state():
    """Test that BaseGenerator provides independent default states."""
    gen = conftest.MockGenerator()
    state1 = gen.default_state()
    state2 = gen.default_state()

    # Should be equal but not the same object
    assert state1 == state2
    assert state1 is not state2

    # Ensure immutability
    assert isinstance(state1.buttons, tuple)
    s1d = state1.to_dict()
    s1d["buttons"][0] = True
    s2d = state2.to_dict()
    assert s2d["buttons"][0] is False

def test_base_modifier_update():
    """Test that BaseModifier's default update returns independent copies."""
    mod = conftest.MockModifier()
    input_state = mod.default_state()

    result = mod.update(input_state)
    input_dict = input_state.to_dict()
    input_dict["axes"][0] = 1.0

    assert result.axes[0] == 0.0

def test_frame_state_validation():
    """Test that FrameState type checking works."""
    from XSerialOne.base import FrameState

    valid_state: FrameState = FrameState()
    
    assert isinstance(valid_state, FrameState)
    assert len(valid_state.buttons) == 10
    assert len(valid_state.axes) == 6
    assert len(valid_state.dpad) == 2