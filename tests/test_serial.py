"""Tests for serial_interface.py functionality."""
import pytest
import struct
from XSerialOne.serial_interface import SerialInterface, Packet

def test_buttons_to_bitmask():
    """Test button array to bitmask conversion."""
    interface = SerialInterface("MOCK")
    
    assert interface.buttons_to_bitmask([False] * 10) == 0
    assert interface.buttons_to_bitmask([True] + [False] * 9) == 1
    assert interface.buttons_to_bitmask([True] * 10) == 0x3FF

def test_dpad_encode():
    """Test dpad tuple to code conversion."""
    interface = SerialInterface("MOCK")
    
    assert interface.dpad_encode((0, 0)) == 4
    assert interface.dpad_encode((0, 1)) == 7
    assert interface.dpad_encode((0, -1)) == 1

def test_send_frame_writes_bytes(mock_serial, basic_frame_state):
    """SerialInterface.send_frame() writes Packet bytes to serial port."""
    interface = SerialInterface("MOCK")
    interface.ser = mock_serial

    interface.send_frame(basic_frame_state)
    
    assert len(mock_serial.written_data) == 1
    written = mock_serial.written_data[0]
    assert isinstance(written, bytes)
    assert written[0] == Packet.HEADER

def test_packet_pack_basic():
    """Test that Packet.pack() produces correctly structured bytes."""
    buttons = 0b101  # example bitmask
    axes = [0.1, -0.2, 0.3]  # fewer than 6 axes, should be padded
    dpad_code = 7

    packet = Packet(buttons=buttons, axes=axes, dpad_code=dpad_code)
    packed = packet.pack()

    assert packed[0] == Packet.HEADER
    payload = packed[1:-1]
    unpacked = struct.unpack('<HffffffB', payload)
    assert unpacked[0] == buttons

    for i, val in enumerate(axes):
        assert unpacked[1+i] == pytest.approx(val)
    for i in range(len(axes), 6):
        assert unpacked[1+i] == 0.0

    assert unpacked[-1] == dpad_code

    expected_checksum = sum(payload) & 0xFF
    assert packed[-1] == expected_checksum