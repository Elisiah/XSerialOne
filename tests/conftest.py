"""Shared pytest fixtures for XSerialOne tests."""
import pytest
import copy
from XSerialOne.base import BaseGenerator, BaseModifier, FrameState

class MockGenerator(BaseGenerator):
    """Test generator that returns configurable states."""
    def __init__(self, states=None):
        super().__init__()
        self.states = states or [self.default_state()]
        self.current = 0
    
    def generate(self) -> FrameState:
        state = self.states[self.current]
        self.current = (self.current + 1) % len(self.states)
        return state

class MockModifier(BaseModifier):
    """Test modifier that applies configurable transforms."""
    def __init__(self, transform_fn=None):
        super().__init__()
        self.transform_fn = transform_fn or (lambda x: copy.deepcopy(x))
    
    def update(self, state: FrameState) -> FrameState:
        return self.transform_fn(state)

@pytest.fixture
def mock_generator():
    """Fixture providing a configurable mock generator."""
    def _create(states=None):
        return MockGenerator(states)
    return _create

@pytest.fixture
def mock_modifier():
    """Fixture providing a configurable mock modifier."""
    def _create(transform_fn=None):
        return MockModifier(transform_fn)
    return _create

@pytest.fixture
def basic_frame_state() -> FrameState:
    """Fixture providing a basic valid frame state."""
    return FrameState()

@pytest.fixture
def mock_serial():
    """Mock serial port for testing serial interface."""
    class MockSerial:
        def __init__(self):
            self.written_data = []
            self.is_open = True
        
        def write(self, data):
            self.written_data.append(data)
            return len(data)
        
        def close(self):
            self.is_open = False
    
    serial = MockSerial()
    return serial

@pytest.fixture
def twitch_event_queue():
    """Fixture providing a TwitchEventQueue."""
    from XSerialOne.extras.modules.twitch_chat import TwitchEventQueue
    return TwitchEventQueue()

@pytest.fixture
def twitch_input_modifier(twitch_event_queue):
    """Fixture providing a TwitchInputModifier."""
    from XSerialOne.extras.modules.twitch_chat import TwitchInputModifier
    return TwitchInputModifier(twitch_event_queue)

@pytest.fixture
def sample_sequence():
    """Fixture providing a simple test sequence."""
    from XSerialOne.sequence import Sequence, SequenceFrame
    
    frames = []
    for i in range(5):
        frame = SequenceFrame(
            timestamp_ms=i * 100.0,
            frame={
                'buttons': [False]*10,
                'axes': [0.5]*6,
                'dpad': (0, 0)
            }
        )
        frames.append(frame)
    
    return Sequence(name="test_sequence", frames=frames)

@pytest.fixture
def input_pipeline():
    """Fixture providing an empty input pipeline."""
    from XSerialOne.pipeline import InputPipeline
    return InputPipeline()

@pytest.fixture
def all_button_states():
    """Fixture providing FrameState with each button pressed."""
    from XSerialOne.frame_constants import Button
    states = []
    for btn_idx in range(10):
        buttons = tuple([i == btn_idx for i in range(10)])
        state = FrameState(
            buttons=buttons,
            axes=tuple([0.0]*6),
            dpad=(0, 0)
        )
        states.append(state)
    return states

@pytest.fixture
def analog_stick_range():
    """Fixture providing FrameState with various analog values."""
    states = [
        FrameState(
            buttons=tuple([False]*10),
            axes=(val/10.0, val/10.0, 0.0, 0.0, 0.0, 0.0),
            dpad=(0, 0)
        )
        for val in range(11)
    ]
    return states