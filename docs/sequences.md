# Sequences

> **About "frames":** In XSerialOne, a *frame* is one unit of controller output sent over the serial connection, not a game render frame. The pipeline evaluates at 1000Hz (every 1ms), but packets are sent to hardware at 200Hz (every 5ms, configurable via `send_interval`). Sequence timestamps are in milliseconds and have no relationship to game frame rate.

Sequences are timestamped recordings of `FrameState` data stored as JSON. Unlike macros, which define scripted reactions to button events, sequences capture exactly what happened and replay it exactly as it was, frame by frame.

Common uses: TAS-style input replay, Rocket League kickoff patterns, repeatable test inputs, recorded combos.

---

## Core types

| Class | Role |
|---|---|
| `Sequence` | Container: a list of `SequenceFrame` objects with a name, description, and total duration |
| `SequenceFrame` | A single frame: `timestamp_ms` (float) + `frame` (dict matching `FrameState.from_dict()`) |
| `SequenceRecorder` | Records frames in real time with accurate timestamps |
| `SequenceRecordingGenerator` | Pipeline generator that records whatever flows through it |
| `SequencePlaybackGenerator` | Pipeline generator that replays a saved `Sequence` |

---

## Recording

### Option A: `SequenceRecorder` (manual)

Use this when you want precise control over start/stop from outside the pipeline.

```python
from XSerialOne import InputPipeline, Sequence
from XSerialOne.sequence import SequenceRecorder
from XSerialOne.modules import XInputGenerator
from XSerialOne.base import BaseModifier, FrameState

recorder = SequenceRecorder()

class RecordingModifier(BaseModifier):
    def update(self, state: FrameState) -> FrameState:
        recorder.record_frame(state)
        return state

pipeline = InputPipeline(None)
pipeline.add_generator(XInputGenerator())
pipeline.add_modifier(RecordingModifier())

recorder.start()
pipeline.run_loop()          # Ctrl+C to stop
sequence = recorder.stop()  # returns a Sequence
sequence.name = "my_combo"
sequence.save("my_combo.json")
```

### Option B: `SequenceRecordingGenerator`

This is a pass-through generator that records everything passing through the pipeline. It also works mid-pipeline if you need to record post-modifier state.

```python
from XSerialOne.modules import XInputGenerator, SequenceRecordingGenerator

recorder_gen = SequenceRecordingGenerator("kickoff", description="Fast kickoff pattern")

pipeline.add_generator(XInputGenerator())
pipeline.add_generate_callback(lambda s: recorder_gen.record_frame(s))

recorder_gen.start_recording()
pipeline.run_loop()
sequence = recorder_gen.stop_recording()
sequence.save("kickoff.json")
```

---

## Playback

```python
from XSerialOne import InputPipeline, Sequence
from XSerialOne.modules import SequencePlaybackGenerator

seq = Sequence.load("kickoff.json")
playback = SequencePlaybackGenerator(seq, speed=1.0, loop=False)
playback.start()

pipeline = InputPipeline("COM3")
pipeline.add_generator(playback)
pipeline.run_loop()
```

### Playback options

| Parameter | Default | Description |
|---|---|---|
| `speed` | `1.0` | Playback speed multiplier. `0.5` = half speed, `2.0` = double. |
| `loop` | `False` | If `True`, restarts from the beginning when the sequence ends. |

### Controlling playback at runtime

```python
playback.pause()        # freeze at current position
playback.resume()       # continue from where it paused
playback.stop()         # reset to beginning, stop playing
playback.start()        # restart from beginning
pos = playback.get_position_ms()   # current timestamp in ms
```

---

## Saving and loading

Sequences are plain JSON: you can open and edit them in any text editor.

```python
sequence.save("path/to/file.json")
seq = Sequence.load("path/to/file.json")
```

Example file structure:
```json
{
  "name": "kickoff",
  "description": "Speed kickoff from right spawn",
  "duration_ms": 1200.0,
  "frames": [
    { "timestamp_ms": 0.0,   "frame": { "buttons": [false, ...], "axes": [0.0, ...], "dpad": [0, 0] } },
    { "timestamp_ms": 16.6,  "frame": { "buttons": [false, ...], "axes": [1.0, ...], "dpad": [0, 0] } }
  ]
}
```

---

## Sequences vs Macros

| | Sequences | Macros |
|---|---|---|
| Activation | Manual (`start()`) or pipeline-driven | Button press, hold, combo, double-tap |
| Content | Exact recorded `FrameState` data | Scripted step-by-step instructions |
| Looping | Optional, at fixed speed | Configurable per activation type |
| Editable without code | Yes, plain JSON | No, requires `MacroBuilder` |
| Best for | Exact reproductions (TAS, kickoffs) | Reactive overlays (rapid fire, anti-recoil) |

---

## Combining sequences and macros

You can trigger a `SequencePlaybackGenerator` from a macro activation by controlling it from a modifier:

```python
from XSerialOne import MacroBuilder, MacroManager, Button
from XSerialOne.base import BaseModifier, FrameState
from XSerialOne.modules import SequencePlaybackGenerator
from XSerialOne import Sequence
import time

seq = Sequence.load("kickoff.json")
playback = SequencePlaybackGenerator(seq)

class KickoffModifier(BaseModifier):
    def __init__(self):
        super().__init__()
        self.manager = MacroManager()
        self.manager.register_macro(
            MacroBuilder("trigger_kickoff")
            .activate_on_press(Button.BACK)
            .build()
        )

    def update(self, state: FrameState) -> FrameState:
        prev = self.manager.update(time.perf_counter(), state)
        # If BACK was just pressed, start the sequence
        if prev != state:
            playback.start()
        return prev
```
