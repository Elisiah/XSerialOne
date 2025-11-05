"""Tests for XInput controller interface."""
import pytest
import ctypes
from unittest.mock import patch, MagicMock
from XSerialOne.modules.xinput import XInputGenerator
from XSerialOne.frame_constants import Axis

@pytest.fixture
def mock_xinput():
    """Create a mock XInput DLL."""
    mock_dll = MagicMock()
    mock_dll.XInputGetState.return_value = 0
    return mock_dll

@pytest.fixture
def generator(mock_xinput):
    """Create an XInputGenerator with a mock DLL."""
    with patch('ctypes.windll') as mock_windll:
        mock_windll.xinput1_4 = mock_xinput
        gen = XInputGenerator()
        gen.xinput = mock_xinput
        return gen

def test_initialization():
    """Test XInput DLL loading and fallback behavior."""
    with patch('ctypes.windll') as mock_windll:
        mock_windll.xinput1_4 = MagicMock()
        gen = XInputGenerator()
        assert gen.xinput == mock_windll.xinput1_4

        del mock_windll.xinput1_4
        mock_windll.xinput9_1_0 = MagicMock()
        gen = XInputGenerator()
        assert gen.xinput == mock_windll.xinput9_1_0

def test_no_controller(generator):
    """Test behavior when no controller is connected."""
    generator.xinput.XInputGetState.return_value = 1167  # ERROR_DEVICE_NOT_CONNECTED
    state = generator.generate()
    
    # Should return default state
    assert all(not b for b in state.buttons)
    assert all(a == 0.0 for a in state.axes)
    assert state.dpad == (0, 0)

def test_button_mapping(generator):
    """Test button bit mapping and state conversion."""
    def create_button_state(button_value):
        state = ctypes.create_string_buffer(20)
        state.raw = (
            b'\x00\x00\x00\x00' +  # Packet number
            button_value.to_bytes(2, 'little') +  # wButtons
            b'\x00' * 14 
        )
        return state

    button_tests = [
        ("A", 0x1000), ("B", 0x2000), ("X", 0x4000), ("Y", 0x8000),
        ("LB", 0x0100), ("RB", 0x0200), ("BACK", 0x0020), ("START", 0x0010),
        ("LS", 0x0040), ("RS", 0x0080)
    ]

    for button_name, button_value in button_tests:
        state = create_button_state(button_value)
        
        def mock_get_state(controller_id, state_ptr):
            state_ptr._obj.raw = state.raw
            return 0

        generator.xinput.XInputGetState.side_effect = mock_get_state
        result = generator.generate()
        
        button_index = list(generator.BUTTON_MAP.keys()).index(button_name)
        assert result.buttons[button_index], f"Button {button_name} should be pressed"

def test_stick_values(generator):
    """Test analog stick value normalization."""
    def create_stick_state(lx, ly, rx, ry):
        state = ctypes.create_string_buffer(20)
        state.raw = (
            b'\x00\x00\x00\x00' +  # Packet number
            b'\x00\x00' +  # wButtons
            b'\x7F\x7F' +  # Triggers at neutral
            lx.to_bytes(2, 'little', signed=True) + 
            ly.to_bytes(2, 'little', signed=True) + 
            rx.to_bytes(2, 'little', signed=True) + 
            ry.to_bytes(2, 'little', signed=True)   
        )
        return state

    test_values = [
        (0, 0, 0, 0),  # Neutral
        (32767, 32767, 32767, 32767),  # Maximum positive
        (-32768, -32768, -32768, -32768),  # Maximum negative
        (16384, -16384, -16384, 16384),  # Mixed values
    ]

    for lx, ly, rx, ry in test_values:
        state = create_stick_state(lx, ly, rx, ry)
        
        def mock_get_state(controller_id, state_ptr):
            state_ptr._obj.raw = state.raw
            return 0

        generator.xinput.XInputGetState.side_effect = mock_get_state
        result = generator.generate()
        
        expected_lx = lx / 32768.0
        expected_ly = -ly / 32768.0 
        expected_rx = rx / 32768.0
        expected_ry = -ry / 32768.0

        assert abs(result.axes[Axis.LEFTSTICKX] - expected_lx) < 0.0001, "Left X value mismatch"
        assert abs(result.axes[Axis.LEFTSTICKY] - expected_ly) < 0.0001, "Left Y value mismatch"
        assert abs(result.axes[Axis.RIGHTSTICKX] - expected_rx) < 0.0001, "Right X value mismatch"
        assert abs(result.axes[Axis.RIGHTSTICKY] - expected_ry) < 0.0001, "Right Y value mismatch"

def test_trigger_values(generator):
    """Test trigger value normalization."""
    def create_trigger_state(lt, rt):
        state = ctypes.create_string_buffer(20)
        state.raw = (
            b'\x00\x00\x00\x00' +  
            b'\x00\x00' +  
            bytes([lt, rt]) +
            b'\x00' * 8  
        )
        return state

    test_values = [
        (0, 0),     
        (255, 255), 
        (128, 128), 
        (64, 192),  
    ]

    for lt, rt in test_values:
        state = create_trigger_state(lt, rt)
        
        def mock_get_state(controller_id, state_ptr):
            state_ptr._obj.raw = state.raw
            return 0

        generator.xinput.XInputGetState.side_effect = mock_get_state
        result = generator.generate()
        
        expected_lt = (lt - 127.5) / 127.5
        expected_rt = (rt - 127.5) / 127.5

        assert abs(result.axes[Axis.LEFTTRIGGER] - expected_lt) < 0.0001, "Left trigger value mismatch"
        assert abs(result.axes[Axis.RIGHTTRIGGER] - expected_rt) < 0.0001, "Right trigger value mismatch"

def test_dpad_values(generator):
    """Test DPAD value conversion."""
    dpad_tests = [
        (0x0001, (0, 1)),   
        (0x0002, (0, -1)),  
        (0x0004, (-1, 0)),  
        (0x0008, (1, 0)),   
        (0x0009, (1, 1)),   
        (0x0006, (-1, -1)), 
    ]

    for button_value, expected_dpad in dpad_tests:
        def mock_get_state(controller_id, state_ptr):
            state_ptr._obj.raw = (
                b'\x00\x00\x00\x00' +  
                button_value.to_bytes(2, 'little') + 
                b'\x00' * 14 
            )
            return 0

        generator.xinput.XInputGetState.side_effect = mock_get_state
        result = generator.generate()
        assert result.dpad == expected_dpad, f"DPAD value mismatch for input {button_value}"