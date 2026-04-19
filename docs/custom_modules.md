# Writing Custom Modules

The pipeline is built around two abstractions: **generators** that produce input and **modifiers** that transform it. Both are simple Python classes, subclass the base class, implement one method, and add it to the pipeline.

---

## FrameState

Every module works with `FrameState`: an immutable snapshot of one controller frame.

```python
from XSerialOne import FrameState, Button, Axis, Dpad

# Always construct with from_dict() - it clamps and validates all values
state = FrameState.from_dict({
    "buttons": [False] * 10,   # indexed by Button enum: A=0, B=1, X=2, Y=3, LB=4, RB=5, BACK=6, START=7, LS=8, RS=9
    "axes":    [0.0]  * 6,     # indexed by Axis enum: LEFTSTICKX=0, LEFTSTICKY=1, RIGHTSTICKX=2, RIGHTSTICKY=3, LEFTTRIGGER=4, RIGHTTRIGGER=5
    "dpad":    (0, 0),         # (x, y), each -1, 0, or 1; use Dpad.UP, Dpad.LEFT etc.
})

# Read values by name
lx   = state.axes[Axis.LEFTSTICKX]
rt   = state.axes[Axis.RIGHTTRIGGER]
a    = state.buttons[Button.A.value]
dpad = state.dpad   # tuple (x, y)
```

`FrameState` is **frozen**: you cannot modify it in place. Modifiers must always return a new instance.

```python
# Pattern for modifying a state in a modifier:
axes = list(state.axes)
axes[Axis.RIGHTSTICKX] = 0.5
return FrameState(buttons=state.buttons, axes=tuple(axes), dpad=state.dpad)

# Or use from_dict for readability:
d = state.to_dict()
d["axes"][Axis.RIGHTSTICKX] = 0.5
return FrameState.from_dict(d)
```

---

## Generators

A generator is the **source** of input each tick. It produces a `FrameState` from nothing: no input state is passed in. The pipeline calls `generate()` at ~200Hz.

```python
from XSerialOne import BaseGenerator, FrameState

class MyGenerator(BaseGenerator):
    def generate(self) -> FrameState:
        return FrameState.from_dict({
            "buttons": [False] * 10,
            "axes": [0.0] * 6,
            "dpad": (0, 0),
        })
```

### Example: sine-wave left stick

```python
import time, math
from XSerialOne import BaseGenerator, FrameState, Axis

class WaveGenerator(BaseGenerator):
    def __init__(self, period: float = 2.0):
        super().__init__()
        self._start = time.perf_counter()
        self._period = period

    def generate(self) -> FrameState:
        t = (time.perf_counter() - self._start) * (2 * math.pi / self._period)
        return FrameState.from_dict({
            "buttons": [False] * 10,
            "axes": [math.sin(t), 0.0, 0.0, 0.0, 0.0, 0.0],
            "dpad": (0, 0),
        })
```

### Example: generator that reads an external source

```python
import requests
from XSerialOne import BaseGenerator, FrameState

class RemoteStateGenerator(BaseGenerator):
    """Polls an HTTP endpoint for controller state (e.g. from another device)."""
    def __init__(self, url: str):
        super().__init__()
        self._url = url
        self._last: FrameState = self.default_state()

    def generate(self) -> FrameState:
        try:
            data = requests.get(self._url, timeout=0.01).json()
            self._last = FrameState.from_dict(data)
        except Exception:
            pass  # keep last known state on failure
        return self._last
```

---

## Modifiers

A modifier receives the current `FrameState` (output of the previous generator or modifier) and returns a new one. Modifiers run in the order they are added to the pipeline.

```python
from XSerialOne import BaseModifier, FrameState

class MyModifier(BaseModifier):
    def update(self, state: FrameState) -> FrameState:
        return state  # pass through unchanged
```

### Example: sensitivity multiplier

```python
from XSerialOne import BaseModifier, FrameState, Axis

class SensitivityModifier(BaseModifier):
    def __init__(self, multiplier: float = 1.5):
        super().__init__()
        self.multiplier = multiplier

    def update(self, state: FrameState) -> FrameState:
        axes = list(state.axes)
        axes[Axis.RIGHTSTICKX] = max(-1.0, min(1.0, axes[Axis.RIGHTSTICKX] * self.multiplier))
        axes[Axis.RIGHTSTICKY] = max(-1.0, min(1.0, axes[Axis.RIGHTSTICKY] * self.multiplier))
        return FrameState(buttons=state.buttons, axes=tuple(axes), dpad=state.dpad)
```

### Example: button remapper

```python
from XSerialOne import BaseModifier, FrameState, Button

class RemapModifier(BaseModifier):
    """Swap two buttons, e.g. make A act as B and vice versa."""
    def __init__(self, a: Button, b: Button):
        super().__init__()
        self._a = a.value
        self._b = b.value

    def update(self, state: FrameState) -> FrameState:
        buttons = list(state.buttons)
        buttons[self._a], buttons[self._b] = buttons[self._b], buttons[self._a]
        return FrameState(buttons=tuple(buttons), axes=state.axes, dpad=state.dpad)
```

### Example: modifier that reacts to its own state over time

Use `TimeAwareMixin` when you need named timers (e.g. "how long has this button been held?").

```python
import time
from XSerialOne import BaseModifier, FrameState, Button, Axis
from XSerialOne.base import TimeAwareMixin

class HoldBoostModifier(BaseModifier, TimeAwareMixin):
    """Gradually increases right trigger the longer LB is held."""

    def update(self, state: FrameState) -> FrameState:
        now = time.perf_counter()
        if state.buttons[Button.LB.value]:
            self.ensure_timer("lb_hold", now)
            held = now - self.get_pipeline_time("lb_hold") if self.get_pipeline_time("lb_hold") else 0
        else:
            self.reset_timer("lb_hold")
            return state

        boost = min(1.0, held / 2.0)   # ramp to full over 2 seconds
        axes = list(state.axes)
        axes[Axis.RIGHTTRIGGER] = boost
        return FrameState(buttons=state.buttons, axes=tuple(axes), dpad=state.dpad)
```

---

## Wiring into the pipeline

```python
from XSerialOne import InputPipeline
from XSerialOne.modules import XInputGenerator, DeadzoneModifier

pipeline = InputPipeline("COM3")         # or None for no hardware
pipeline.add_generator(XInputGenerator())
pipeline.add_modifier(DeadzoneModifier(deadzone_left=0.1, deadzone_right=0.1))
pipeline.add_modifier(SensitivityModifier(multiplier=1.3))
pipeline.add_modifier(HoldBoostModifier())
pipeline.run_loop()
```

Modifiers run in the order added. The output of modifier N is the input to modifier N+1.

### Pipeline callbacks

Two hooks let you inspect state at different points without inserting a modifier:

```python
# Called after generate(), before modifiers - see the raw input
pipeline.add_generate_callback(lambda s: print("raw:", s.axes[0]))

# Called after all modifiers - see the final output
pipeline.add_post_mod_callback(lambda s: print("final:", s.axes[0]))
```

The `DebugViewer` uses both to render the before/after comparison view.

---

## Packaging your module

Any module can live anywhere on the Python path: there is no registration step.

```
my_project/
├── my_mods/
│   ├── __init__.py
│   ├── camera_generator.py
│   └── aim_assist.py
└── main.py
```

```python
# main.py
from XSerialOne import InputPipeline
from my_mods.camera_generator import CameraGenerator
from my_mods.aim_assist import AimAssistModifier

pipeline = InputPipeline("COM3")
pipeline.add_generator(CameraGenerator())
pipeline.add_modifier(AimAssistModifier())
pipeline.run_loop()
```
