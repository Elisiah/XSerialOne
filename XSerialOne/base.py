"""
base.py
Author: Ellie V.

Core base classes and data structures for the XSerialOne framework.

This module defines the fundamental components used throughout the framework,
including the immutable FrameState class for representing controller state,
and abstract base classes for input generators and modifiers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple, List, Dict, Any
import copy


@dataclass(frozen=True)
class FrameState:
    """Immutable frame state for the pipeline.

    Use `FrameState.from_dict()` to create from a mapping, and
    `to_dict()` to get a plain dict for compatibility with legacy code.
    """
    buttons: Tuple[bool, ...] = tuple([False] * 10)
    axes: Tuple[float, ...] = tuple([0.0] * 6)
    dpad: Tuple[int, int] = (0, 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buttons": list(self.buttons),
            "axes": list(self.axes),
            "dpad": tuple(self.dpad),
        }

    @staticmethod
    def _normalize_values(obj: Dict[str, Any]) -> Dict[str, Any]:
        out = {
            "buttons": [False] * 10,
            "axes": [0.0] * 6,
            "dpad": (0, 0),
        }

        if not isinstance(obj, dict):
            return out

        buttons = obj.get("buttons")
        if isinstance(buttons, (list, tuple)):
            b = [bool(x) for x in buttons]
            b = (b + [False] * 10)[:10]
            out["buttons"] = b

        axes = obj.get("axes")
        if isinstance(axes, (list, tuple)):
            def _to_float_clamped(x):
                try:
                    v = float(x)
                except Exception:
                    return 0.0
                return max(-1.0, min(1.0, v))
            a = [_to_float_clamped(x) for x in axes]
            a = (a + [0.0] * 6)[:6]
            out["axes"] = a

        dpad = obj.get("dpad")
        if isinstance(dpad, (list, tuple)) and len(dpad) >= 2:
            try:
                hx = int(dpad[0])
                hy = int(dpad[1])
                hx = max(-1, min(1, hx))
                hy = max(-1, min(1, hy))
                out["dpad"] = (hx, hy)
            except Exception:
                pass

        return out

    @classmethod
    def from_dict(cls, obj: Dict[str, Any]) -> "FrameState":
        data = cls._different_input(obj) if False else cls._normalize_values(obj)
        return cls(buttons=tuple(data["buttons"]), axes=tuple(data["axes"]), dpad=tuple(data["dpad"]))

    @staticmethod
    def _different_input(obj: Dict[str, Any]) -> Dict[str, Any]:
        return FrameState._normalize_values(obj)


class BaseModule(ABC):
    def default_state(self) -> FrameState:
        return FrameState()


class BaseGenerator(BaseModule, ABC):
    @abstractmethod
    def generate(self) -> FrameState:
        raise NotImplementedError


class BaseModifier(BaseModule, ABC):
    @abstractmethod
    def update(self, state: FrameState) -> FrameState:
        raise NotImplementedError