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