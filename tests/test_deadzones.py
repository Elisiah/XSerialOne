"""Tests for deadzones.py module."""
import pytest
import copy
from XSerialOne.base import FrameState
from XSerialOne.modules.deadzones import DeadzoneModifier, HairTriggers
from XSerialOne.frame_constants import Axis

def test_deadzone_initialization():
    """Test that modifier initializes with correct default values."""
    modifier = DeadzoneModifier()
    assert modifier.deadzone_left == 0.2
    assert modifier.deadzone_right == 0.2

    custom = DeadzoneModifier(deadzone_left=0.3, deadzone_right=0.4)
    assert custom.deadzone_left == 0.3
    assert custom.deadzone_right == 0.4

def test_no_change_above_threshold(basic_frame_state):
    """Test that values above deadzone remain unchanged."""
    modifier = DeadzoneModifier(deadzone_left=0.2, deadzone_right=0.2)
    state = FrameState(
        buttons=basic_frame_state.buttons,
        axes=(0.5, 0.5, 0.5, 0.5, 0, 0),
        dpad=basic_frame_state.dpad
    )
    result = modifier.update(state)
    assert result.axes[:4] == state.axes[:4]

def test_deadzone_threshold_boundary():
    """Test behavior at the deadzone threshold boundary."""
    modifier = DeadzoneModifier(deadzone_left=0.2, deadzone_right=0.2)
    
    # Test just below threshold
    state = FrameState(
        buttons=(False,)*10,
        axes=(0.19, 0.19, 0.19, 0.19, 0, 0),
        dpad=(0, 0)
    )
    result = modifier.update(state)
    assert all(axis == 0.0 for axis in result.axes[:4])

    # Test exactly at threshold
    state = FrameState(
        buttons=(False,)*10,
        axes=(0.2, 0.2, 0.2, 0.2, 0, 0),
        dpad=(0, 0)
    )
    result = modifier.update(state)
    assert all(axis == 0.2 for axis in result.axes[:4])

    # Test just above threshold
    state = FrameState(
        buttons=(False,)*10,
        axes=(0.21, 0.21, 0.21, 0.21, 0, 0),
        dpad=(0, 0)
    )
    result = modifier.update(state)
    assert all(axis == 0.21 for axis in result.axes[:4])

@pytest.mark.parametrize("test_value", [
    -1.0, -0.5, -0.25, 0.25, 0.5, 1.0
])
def test_deadzone_scaling(test_value):
    """Test that deadzone is applied symmetrically to positive and negative values."""
    modifier = DeadzoneModifier(deadzone_left=0.2, deadzone_right=0.2)
    state = FrameState(
        buttons=(False,)*10,
        axes=(test_value,)*4 + (0, 0),
        dpad=(0, 0)
    )
    result = modifier.update(state)
    
    if abs(test_value) <= 0.2:
        assert all(axis == 0.0 for axis in result.axes[:4])
    else:
        assert all(axis == test_value for axis in result.axes[:4])

def test_deadzone_independence():
    """Test that left and right stick deadzones are independent."""
    modifier = DeadzoneModifier(deadzone_left=0.1, deadzone_right=0.3)
    state = FrameState(
        buttons=(False,)*10,
        axes=(0.2, 0.2, 0.2, 0.2, 0, 0),
        dpad=(0, 0)
    )
    result = modifier.update(state)
    
    assert result.axes[Axis.LEFTSTICKX] == 0.2
    assert result.axes[Axis.LEFTSTICKY] == 0.2
    assert result.axes[Axis.RIGHTSTICKX] == 0.0
    assert result.axes[Axis.RIGHTSTICKY] == 0.0

def test_deadzone_preserves_other_axes():
    """Test that non-stick axes (triggers) are preserved."""
    modifier = DeadzoneModifier(deadzone_left=0.2, deadzone_right=0.2)
    state = FrameState(
        buttons=(False,)*10,
        axes=(0, 0, 0, 0, 0.7, 0.9), 
        dpad=(0, 0)
    )
    result = modifier.update(state)
    assert result.axes[4:] == state.axes[4:]

def test_deadzone_state_immutability(basic_frame_state):
    """Test that DeadzoneModifier.update does not modify the original state."""
    modifier = DeadzoneModifier()
    
    state = FrameState(
        buttons=basic_frame_state.buttons,
        axes=(0.1, 0.1, 0.1, 0.1, 0, 0),
        dpad=basic_frame_state.dpad
    )
    
    original_state = copy.deepcopy(state)
    result = modifier.update(state)
    
    assert state.buttons == original_state.buttons
    assert state.axes == original_state.axes
    assert state.dpad == original_state.dpad

# -----------------------

def test_hair_trigger_initialization():
    """Test that hair trigger modifier initializes correctly."""
    modifier = HairTriggers()
    assert modifier.threshold == 0.1

    custom = HairTriggers(threshold=0.2)
    assert custom.threshold == 0.2

def test_hair_trigger_threshold_boundary():
    """Test behavior at the hair trigger threshold boundary."""
    modifier = HairTriggers(threshold=0.1)
    
    # Test below threshold
    state = FrameState(
        buttons=(False,)*10,
        axes=(0, 0, 0, 0, 0, 0.09),
        dpad=(0, 0)
    )
    result = modifier.update(state)
    assert result.axes[Axis.RIGHTTRIGGER] == -1.0

    # Test at threshold
    state = FrameState(
        buttons=(False,)*10,
        axes=(0, 0, 0, 0, 0, 0.1),
        dpad=(0, 0)
    )
    result = modifier.update(state)
    assert result.axes[Axis.RIGHTTRIGGER] == -1.0

    # Test above threshold
    state = FrameState(
        buttons=(False,)*10,
        axes=(0, 0, 0, 0, 0, 0.11),
        dpad=(0, 0)
    )
    result = modifier.update(state)
    assert result.axes[Axis.RIGHTTRIGGER] == 1.0

def test_hair_trigger_preserves_other_values():
    """Test that hair trigger only affects RT axis."""
    modifier = HairTriggers()
    state = FrameState(
        buttons=(True, False, True),
        axes=(0.5, -0.5, 0.2, -0.2, 0.7, 0.5),
        dpad=(1, -1)
    )
    result = modifier.update(state)
    
    assert result.buttons == state.buttons
    assert result.axes[:5] == state.axes[:5]
    assert result.dpad == state.dpad
    
    assert result.axes[Axis.RIGHTTRIGGER] == 1.0

def test_hair_trigger_state_immutability():
    """Test that HairTriggers.update does not modify the original state."""
    modifier = HairTriggers()
    state = FrameState(
        buttons=(False,) * 10,
        axes=(0, 0, 0, 0, 0, 0.5),
        dpad=(0, 0)
    )
    original_state = copy.deepcopy(state)
    modifier.update(state)

    assert state.buttons == original_state.buttons
    assert state.axes == original_state.axes
    assert state.dpad == original_state.dpad

@pytest.mark.parametrize("trigger_value,expected", [
    (-1.0, -1.0),
    (-0.5, -1.0),
    (0.0, -1.0),
    (0.05, -1.0),
    (0.15, 1.0),
    (0.5, 1.0),
    (1.0, 1.0)
])
def test_hair_trigger_values(trigger_value, expected):
    """Test hair trigger behavior across range of input values."""
    modifier = HairTriggers(threshold=0.1)
    state = FrameState(
        buttons=(False,)*10,
        axes=(0, 0, 0, 0, 0, trigger_value),
        dpad=(0, 0)
    )
    result = modifier.update(state)
    assert result.axes[Axis.RIGHTTRIGGER] == expected