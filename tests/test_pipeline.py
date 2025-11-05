"""Tests for pipeline.py functionality."""
import pytest
from XSerialOne.pipeline import InputPipeline
from XSerialOne.serial_interface import SerialInterface
from XSerialOne.base import FrameState
from XSerialOne.frame_constants import Axis, Button

def test_pipeline_combine_generators(mock_generator, basic_frame_state):
    """Test that pipeline correctly combines generator outputs."""
    gen1 = mock_generator([basic_frame_state])
    gen2 = mock_generator([FrameState(buttons=tuple([True]*10), axes=tuple([1.0]*6), dpad=(1,1))])
    
    pipeline = InputPipeline()
    pipeline.add_generator(gen1)
    pipeline.add_generator(gen2)
    
    # By default it takes first generator (further logic may be added later)
    state = pipeline.combine_generators()
    assert state == basic_frame_state

def test_pipeline_apply_modifiers(mock_modifier, basic_frame_state):
    """Test that modifiers are applied in sequence."""
    def modifier1(state: FrameState) -> FrameState:
        axes = list(state.axes)
        axes[Axis.LEFTSTICKX] = 1.0
        return FrameState(buttons=state.buttons, axes=tuple(axes), dpad=state.dpad)

    def modifier2(state: FrameState) -> FrameState:
        buttons = list(state.buttons)
        buttons[Button.A] = True
        return FrameState(buttons=tuple(buttons), axes=state.axes, dpad=state.dpad)
    
    pipeline = InputPipeline()
    pipeline.add_modifier(mock_modifier(modifier1))
    pipeline.add_modifier(mock_modifier(modifier2))
    
    result = pipeline.apply_modifiers(basic_frame_state)
    assert result.axes[Axis.LEFTSTICKX] == 1.0
    assert result.buttons[Button.A] is True

def test_pipeline_update_sends_to_serial(mock_generator, mock_serial, basic_frame_state):
    """Test that pipeline.update sends frame to serial interface."""
    pipeline = InputPipeline(serial_port="MOCK", baud=115200)
    si = SerialInterface(serial_port := "MOCK")
    si.ser = mock_serial
    pipeline.serial = si
    
    pipeline.add_generator(mock_generator([basic_frame_state]))
    pipeline.update()
    
    assert len(mock_serial.written_data) == 1