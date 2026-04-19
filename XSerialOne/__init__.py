"""XSerialOne package initializer."""

from XSerialOne.base import BaseGenerator, BaseModifier, FrameState, TimeAwareMixin
from XSerialOne.debug_viewer import DebugViewer
from XSerialOne.frame_constants import Axis, Button, Dpad
from XSerialOne.input_detection import InputDetector
from XSerialOne.macro_builder import MacroBuilder
from XSerialOne.macro_system import (
    ActivationCondition,
    Macro,
    MacroManager,
    MacroOutput,
    MacroState,
    MacroType,
    ParallelAction,
)
from XSerialOne.pipeline import InputPipeline
from XSerialOne.sequence import Sequence, SequenceFrame, SequenceRecorder
from XSerialOne.serial_interface import SerialInterface

__all__ = [
    # Core
    "BaseGenerator", "BaseModifier", "FrameState", "TimeAwareMixin",
    "InputPipeline",
    "SerialInterface",
    "DebugViewer",
    # Constants
    "Button", "Axis", "Dpad",
    # Macro system
    "Macro", "MacroManager", "MacroType", "MacroState",
    "MacroOutput", "ActivationCondition", "ParallelAction",
    "MacroBuilder",
    # Sequence system
    "Sequence", "SequenceFrame", "SequenceRecorder",
    # Input detection
    "InputDetector",
]
