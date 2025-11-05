"""Tests for antirecoil.py module."""
import pytest
from XSerialOne.base import FrameState
from XSerialOne.modules.antirecoil import BasicAntiRecoilModifier
from XSerialOne.frame_constants import Axis

def test_antirecoil_initialization():
    """Test that modifier initializes with correct default values."""
    modifier = BasicAntiRecoilModifier()
    assert modifier.recoil_strength == 0.3
    assert modifier.trigger_threshold == 0.1

def test_no_trigger_no_change(basic_frame_state):
    """Test that no recoil is applied when trigger is below threshold."""
    modifier = BasicAntiRecoilModifier()
    state = FrameState(
        buttons=basic_frame_state.buttons,
        axes=(0, 0, 0, 0, 0, 0),
        dpad=basic_frame_state.dpad
    )
    result = modifier.update(state)
    assert result.axes == state.axes

def test_trigger_threshold_boundary(basic_frame_state):
    """Test behavior at the trigger threshold boundary."""
    modifier = BasicAntiRecoilModifier()
    
    # Test just below threshold
    state = FrameState(
        buttons=basic_frame_state.buttons,
        axes=(0, 0, 0, 0, 0, 0.099),
        dpad=basic_frame_state.dpad
    )
    result = modifier.update(state)
    assert result.axes[Axis.RIGHTSTICKY] == 0 

    # Test at threshold
    state = FrameState(
        buttons=basic_frame_state.buttons,
        axes=(0, 0, 0, 0, 0, 0.1), 
        dpad=basic_frame_state.dpad
    )
    result = modifier.update(state)
    assert result.axes[Axis.RIGHTSTICKY] > 0 

def test_full_trigger_pull(basic_frame_state):
    """Test recoil at maximum trigger pull."""
    modifier = BasicAntiRecoilModifier()
    state = FrameState(
        buttons=basic_frame_state.buttons,
        axes=(0, 0, 0, 0, 0, 1.0),
        dpad=basic_frame_state.dpad
    )
    result = modifier.update(state)
    assert result.axes[Axis.RIGHTSTICKY] == modifier.recoil_strength

@pytest.mark.parametrize("trigger", [0.25, 0.5, 0.75, 1.0])
def test_recoil_scaling(basic_frame_state, trigger):
    """Test that recoil scales properly with trigger pull."""
    modifier = BasicAntiRecoilModifier()
    state = FrameState(
        buttons=basic_frame_state.buttons,
        axes=(0, 0, 0, 0, 0, trigger),
        dpad=basic_frame_state.dpad
    )
    result = modifier.update(state)
    expected_recoil = modifier.recoil_strength * (trigger / 1.0)
    assert abs(result.axes[Axis.RIGHTSTICKY] - expected_recoil) < 0.0001

@pytest.mark.parametrize("rx,ry", [
    (0.5, 0),    # Aiming right
    (-0.5, 0),   # Aiming left
    (0, 0.5),    # Aiming up
    (0, -0.5),   # Aiming down
    (0.5, 0.5),  # Aiming diagonal
])
def test_aim_direction_compensation(basic_frame_state, rx, ry):
    """Test recoil with different aim directions."""
    modifier = BasicAntiRecoilModifier()
    state = FrameState(
        buttons=basic_frame_state.buttons,
        axes=(0, 0, rx, ry, 0, 1.0),  # Full trigger
        dpad=basic_frame_state.dpad
    )
    result = modifier.update(state)
    assert result.axes[Axis.RIGHTSTICKX] == rx
    assert result.axes[Axis.RIGHTSTICKY] > ry

def test_negligible_movement(basic_frame_state):
    """Test recoil behavior with very small stick movement."""
    modifier = BasicAntiRecoilModifier()
    state = FrameState(
        buttons=basic_frame_state.buttons,
        axes=(0, 0, 0.009, 0.009, 0, 1.0),
        dpad=basic_frame_state.dpad
    )
    result = modifier.update(state)
    assert result.axes[Axis.RIGHTSTICKY] == 0.009 + modifier.recoil_strength 

def test_state_immutability(basic_frame_state):
    """Test that the original state is not modified."""
    modifier = BasicAntiRecoilModifier()
    state = FrameState(
        buttons=basic_frame_state.buttons,
        axes=(0, 0, 0.5, 0.5, 0, 1.0),
        dpad=basic_frame_state.dpad
    )
    original_axes = state.axes
    modifier.update(state)
    assert state.axes == original_axes

def test_button_preservation():
    """Test that button states are preserved."""
    modifier = BasicAntiRecoilModifier()
    state = FrameState(
        buttons=(True, False, True, False, False, True, False, False, True, False),
        axes=(0, 0, 0, 0, 0, 1.0),
        dpad=(1, -1)
    )
    result = modifier.update(state)
    assert result.buttons == state.buttons
    assert result.dpad == state.dpad

def test_extreme_values(basic_frame_state):
    """Test behavior with extreme input values."""
    modifier = BasicAntiRecoilModifier()
    state = FrameState(
        buttons=basic_frame_state.buttons,
        axes=(1.0, 1.0, 1.0, 1.0, 1.0, 1.0),
        dpad=basic_frame_state.dpad
    )
    result = modifier.update(state)
    
    # Ensure preservation of changes to non-modified axes
    assert result.axes[Axis.LEFTSTICKX] == 1.0
    assert result.axes[Axis.LEFTSTICKY] == 1.0
    assert result.axes[Axis.RIGHTSTICKX] == 1.0
    assert result.axes[Axis.LEFTTRIGGER] == 1.0

    # Ensure correctness in modifies axes
    expected_recoil = 1.0 + (modifier.recoil_strength * (1.0 / 1.0))
    assert result.axes[Axis.RIGHTSTICKY] == expected_recoil

def test_rapid_trigger_changes(basic_frame_state):
    """Test behavior with rapidly changing trigger values."""
    modifier = BasicAntiRecoilModifier()
    trigger_sequence = [0, 1.0, 0.3, 0.8, 0.1, 0.9, 0]
    previous_recoil = None
    
    for trigger in trigger_sequence:
        state = FrameState(
            buttons=basic_frame_state.buttons,
            axes=(0, 0, 0, 0, 0, trigger),
            dpad=basic_frame_state.dpad
        )
        result = modifier.update(state)
        current_recoil = result.axes[Axis.RIGHTSTICKY]
        
        if previous_recoil is not None:
            if trigger >= modifier.trigger_threshold:
                assert abs(current_recoil - (modifier.recoil_strength * trigger)) < 0.0001
            else:
                assert current_recoil == 0
        
        previous_recoil = current_recoil