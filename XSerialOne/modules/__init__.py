"""XSerialOne.modules package initializer."""

from .anti_afk import AntiAFKModifier
from .antirecoil import BasicAntiRecoilModifier
from .deadzones import DeadzoneModifier, HairTriggers
from .sequence_playback import SequencePlaybackGenerator, SequenceRecordingGenerator
from .xinput import XInputGenerator

__all__ = [
    "XInputGenerator",
    "BasicAntiRecoilModifier",
    "DeadzoneModifier", "HairTriggers",
    "SequencePlaybackGenerator", "SequenceRecordingGenerator",
    "AntiAFKModifier",
]
