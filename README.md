# XSerialOne

![CI](https://github.com/Elisiah/XSerialOne/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Control an Xbox console with code. XSerialOne is a Python framework for generating and modifying simulated controller inputs in real time, whether you're building Twitch chaos modes, accessible gaming tools, or automated input for testing.

Unlike Titan Two and Cronus Zen (closed Lua/GPC ecosystems locked to embedded hardware), XSerialOne runs on a full Python environment. Any Python library, OpenCV, MediaPipe, speech recognition, ML models, becomes a first-class input source.

> **Disclaimer:** This project is an educational exercise in understanding console input systems. Hardware designs will not be published to avoid promoting cheating. Users are responsible for complying with platform terms of service.

---

## Architecture

```
  ┌────────────────────────────────────────────────────────────┐
  │                      InputPipeline (~200Hz)                │
  │                                                            │
  │  ┌──────────────────┐     ┌────────────────────────────┐   │
  │  │    Generator     │───▶│  Modifier  ▶  Modifier  ▶ │   │
  │  │                  │     │                            │   │
  │  │  XInputGenerator │     │  DeadzoneModifier          │   │
  │  │  SeqPlayback     │     │  BasicAntiRecoilModifier   │   │
  │  │  CircleGenerator │     │  AntiAFKModifier           │   │
  │  │  custom…         │     │  MacroModifier, custom…    │   │
  │  └──────────────────┘     └──────────────┬─────────────┘   │
  │                                          │  FrameState     │
  └──────────────────────────────────────────┼─────────────────┘
                                             │
                                             ▼
                                    SerialInterface
                                             │
                          ┌──────────────────┴──────────────────┐
                          │                                     │
                   XSerialOne Device                       port=None
                    (real hardware)                      (simulate mode)
                          │
                          ▼
                        Xbox
```

---

## Installation

```bash
git clone https://github.com/Elisiah/XSerialOne.git
cd XSerialOne
pip install -e .
```

**No hardware?** Run the simulate example to see the full pipeline in action:

```bash
python examples/simulate.py
```

---

## Quick Start

```python
from XSerialOne import InputPipeline, DebugViewer
from XSerialOne.modules import XInputGenerator, DeadzoneModifier, BasicAntiRecoilModifier

pipeline = InputPipeline("COM3")        # pass None to run without hardware
pipeline.add_generator(XInputGenerator())
pipeline.add_modifier(DeadzoneModifier(deadzone_left=0.1, deadzone_right=0.1))
pipeline.add_modifier(BasicAntiRecoilModifier())

viewer = DebugViewer(show_second_screen=True)
viewer.attach_to_pipeline(pipeline)
viewer.start()

try:
    pipeline.run_loop()
finally:
    viewer.stop()
```

---

## Writing Custom Modules

> Full guide with more examples at [`docs/custom_modules.md`](docs/custom_modules.md).

### Generator: produces input each tick

```python
from XSerialOne import BaseGenerator, FrameState

class MyGenerator(BaseGenerator):
    def generate(self) -> FrameState:
        return FrameState.from_dict({
            "buttons": [False] * 10,
            "axes": [0.0] * 6,   # LX, LY, RX, RY, LT, RT  (-1.0 to 1.0)
            "dpad": (0, 0)       # each axis: -1, 0, or 1
        })
```

### Modifier, transforms a frame each tick

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

---

## Macro System

Event-triggered input overlays built with a fluent DSL. Macros activate on button presses, holds, combos, or double-taps and are merged into the frame each tick by `MacroManager`.

```python
from XSerialOne import MacroBuilder, MacroManager, Button, Axis
from XSerialOne.base import BaseModifier, FrameState
import time

boost = (
    MacroBuilder("boost")
    .activate_on_hold(Button.LB, hold_duration=0.3)
    .trigger(Axis.RIGHTTRIGGER, 1.0).wait_ms(100)
    .build(loop=True)
)

class MacroModifier(BaseModifier):
    def __init__(self):
        super().__init__()
        self.manager = MacroManager()
        self.manager.register_macro(boost)

    def update(self, state: FrameState) -> FrameState:
        return self.manager.update(time.perf_counter(), state)
```

| Builder method | Loops | Description |
|---|---|---|
| `activate_on_press` | Add `build(loop=True)` to loop | Fires once on the rising edge of a button press. With `loop=True`: first press starts, second press stops (toggle). |
| `activate_on_hold` | No | Fires once after the button is held for `hold_ms` (default 500ms). |
| `activate_on_combo` | Add `build(loop=True)` to loop | Fires once when all specified buttons are held simultaneously. With `loop=True`: toggle like `on_press`. |
| `activate_on_double_tap` | No | Fires once when the button is pressed twice within 300ms. |
| `activate_while_held_state` | Holds last frame | Runs the sequence once, then **freezes on the final step's output** for as long as the condition is held. Releases on button up. |
| `activate_while_held_sequence` | While held | Continuously repeats the full sequence for as long as the condition is held. Releases on button up. |

> See [`docs/macros.md`](docs/macros.md) for full examples and the `LOOP_LAST` advanced type.

---

## Sequence System

Record controller input to JSON and replay it exactly. Sequences capture a timestamped stream of `FrameState` data, distinct from macros, which define scripted reactions to inputs.

> See [`docs/sequences.md`](docs/sequences.md) for recording, editing, and playback details.

```python
# Play back a saved sequence
from XSerialOne import InputPipeline, Sequence
from XSerialOne.modules import SequencePlaybackGenerator

seq = Sequence.load("kickoff.json")
playback = SequencePlaybackGenerator(seq, speed=1.0, loop=False)
playback.start()

pipeline = InputPipeline("COM3")
pipeline.add_generator(playback)
pipeline.run_loop()
```

---

## Included Modules

| Import | Class | Description |
|---|---|---|
| `modules.xinput` | `XInputGenerator` | Reads a physical Xbox controller via XInput (Windows) |
| `modules.deadzones` | `DeadzoneModifier` | Circular per-stick deadzone with smooth rescaling |
| `modules.deadzones` | `HairTriggers` | Snaps triggers to full at a threshold |
| `modules.antirecoil` | `BasicAntiRecoilModifier` | Upward stick push proportional to right trigger |
| `modules.sequence_playback` | `SequencePlaybackGenerator` | Replays a saved `Sequence` |
| `modules.sequence_playback` | `SequenceRecordingGenerator` | Records frames passing through the pipeline |
| `modules.anti_afk` | `AntiAFKModifier` | Looping movement to prevent AFK kicks |

---

## Extras

Optional modules for content-creator and advanced use cases. Clone the extras repository to enable them:

```bash
git clone https://github.com/Elisiah/XSerialOne-extras.git XSerialOne/extras
```

| Module | Description |
|---|---|
| `extras.modules.twitch_chat` | Twitch IRC + EventSub → controller input |
| `extras.modules.twoplayer` | WebSocket relay for two-player merged control |
| `extras.modules.frame_randomizer` | Hotkey-triggered input mapping randomisation |
| `extras.flashbang` | Pygame overlay for Twitch channel point redemptions |
| `extras.macro_editor_gui` | Pygame GUI for building macros without code |

---

## Development

```bash
pip install -r test-requirements.txt
pytest tests/                             # all tests
pytest tests/test_pipeline.py             # single file
pytest -v --cov=XSerialOne tests/         # with coverage
python examples/simulate.py               # run without hardware
```

---

## Project Structure

```
XSerialOne/
├── base.py                  # FrameState, BaseGenerator, BaseModifier, TimeAwareMixin
├── pipeline.py              # InputPipeline, tick loop, callbacks, serial dispatch
├── serial_interface.py      # Packet serialization, SerialInterface (MOCK support)
├── frame_constants.py       # Button, Axis, Dpad enums
├── debug_viewer.py          # Pygame real-time visualizer
├── input_detection.py       # InputDetector, press/hold/combo/double-tap events
├── macro_system.py          # Macro, MacroManager, activation/output types
├── macro_builder.py         # MacroBuilder fluent DSL
├── sequence.py              # Sequence, SequenceFrame, SequenceRecorder
├── modules/                 # Built-in generators and modifiers
└── extras/                  # Optional extras (clone XSerialOne-extras here)
examples/
├── simulate.py              # Full pipeline demo, no hardware required
└── …
tests/
```
