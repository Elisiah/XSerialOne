# Macros

> **About "frames":** In XSerialOne, a *frame* is one unit of controller output sent over the serial connection, not a game render frame. The pipeline evaluates at 1000Hz (every 1ms), but packets are sent to hardware at 200Hz (every 5ms, configurable via `send_interval`). Macro step durations are specified in milliseconds and have no relationship to game frame rate.

Macros are scripted input overlays that activate in response to controller events. They run in parallel with normal input: the `MacroManager` merges their output into the live `FrameState` each tick, so a macro can press a button or push a stick without overriding everything else.

---

## How it works

1. Define a `Macro` using `MacroBuilder`: a sequence of steps, each with button/axis changes and a duration.
2. Register it with a `MacroManager`.
3. Wrap the manager in a `BaseModifier` and add it to the pipeline.
4. Each tick, `MacroManager.update(now, state)` checks activation conditions, advances running macros, and returns a modified `FrameState`.

```python
from XSerialOne import MacroBuilder, MacroManager, Button, Axis
from XSerialOne.base import BaseModifier, FrameState
import time

class MyMacroModifier(BaseModifier):
    def __init__(self):
        super().__init__()
        self.manager = MacroManager()
        self.manager.register_macro(
            MacroBuilder("jump")
            .activate_on_press(Button.A)
            .press(Button.A).wait_ms(80)
            .release(Button.A).wait_ms(20)
            .build()
        )

    def update(self, state: FrameState) -> FrameState:
        return self.manager.update(time.perf_counter(), state)
```

---

## Building steps

Each call to `.press()`, `.release()`, `.stick()`, or `.trigger()` sets output for the **current step**. Calling `.wait()` or `.wait_ms()` commits the current step (with its duration) and starts a new one.

```python
MacroBuilder("recoil_control")
    .activate_while_held_state(RIGHTTRIGGER=0.5)   # trigger-based activation
    .stick(Axis.RIGHTSTICKY, -0.3).wait_ms(400)    # step 1: pull down for 400ms
    .stick(Axis.RIGHTSTICKY, -0.5).wait_ms(400)    # step 2: pull harder for 400ms
    .stick(Axis.RIGHTSTICKY, -0.7)                 # step 3: final state (no wait = held)
    .build()
```

If the last step has no `.wait()`, it becomes the terminal state, relevant for `while_held_state` which freezes on it.

---

## Activation types

### `activate_on_press(*buttons)`
Fires **once** on the rising edge of the button(s). Reruns each time the button is re-pressed after being released.

```python
MacroBuilder("quick_melee")
    .activate_on_press(Button.RB)
    .press(Button.RB).wait_ms(50)
    .release(Button.RB).wait_ms(50)
    .build()
```

### `activate_on_press` + `build(loop=True)` → toggle loop
`build(loop=True)` converts any activation to a **toggle loop**. First press starts the sequence looping continuously; pressing the activation again stops it. Only one `LOOP` macro runs at a time: starting a new one stops any other running loop.

```python
MacroBuilder("rapid_fire")
    .activate_on_press(Button.RT)        # press once to start, again to stop
    .trigger(Axis.RIGHTTRIGGER, 1.0).wait_ms(15)
    .trigger(Axis.RIGHTTRIGGER, 0.0).wait_ms(15)
    .build(loop=True)                    # ← makes this a toggle
```

> **Note:** `build(loop=True)` always produces a toggle loop regardless of which `activate_*` method you called. If you need hold-triggered looping, use `activate_while_held_sequence` instead.

### `activate_on_hold(*buttons, hold_ms=500)`
Fires **once** after the button has been held for `hold_ms` milliseconds (default 500ms). Does not loop.

```python
MacroBuilder("super_move")
    .activate_on_hold(Button.LB, hold_ms=800)
    .press(Button.X, Button.Y).wait_ms(100)
    .release(Button.X, Button.Y)
    .build()
```

### `activate_on_combo(*buttons)`
Fires **once** when all specified buttons are held simultaneously (rising edge). Functionally identical to `on_press` but semantically distinct: use this when multiple buttons must be held at once.

```python
MacroBuilder("anti_afk")
    .activate_on_combo(Button.LB, dpad=Dpad.DOWN)  # LB + D-pad down together
    .stick(Axis.LEFTSTICKY, -1.0).wait(2.0)
    .stick(Axis.LEFTSTICKY,  1.0).wait(2.0)
    .build(loop=True)
```

### `activate_on_double_tap(*buttons)`
Fires **once** when the button is pressed twice within **300ms**.

```python
MacroBuilder("dodge")
    .activate_on_double_tap(Button.A)
    .press(Button.B).wait_ms(60)
    .release(Button.B)
    .build()
```

### `activate_while_held_state(*buttons / triggers)`
Runs the sequence **once**, then **freezes on the final step's output** for as long as the condition is held. Stops and releases everything when the button is released. Good for progressive effects like recoil compensation that should hold at maximum.

```python
MacroBuilder("aim_assist")
    .activate_while_held_state(LEFTTRIGGER=0.5)   # while LT past threshold
    .stick(Axis.RIGHTSTICKY, -0.1).wait_ms(200)   # ramp up
    .stick(Axis.RIGHTSTICKY, -0.2).wait_ms(200)
    .stick(Axis.RIGHTSTICKY, -0.3)                # held here until LT released
    .build()
```

### `activate_while_held_sequence(*buttons / triggers)`
**Continuously repeats** the full sequence for as long as the condition is held. Stops and releases when the button is released. Good for rhythmic effects that should keep cycling.

```python
MacroBuilder("rapid_while_held")
    .activate_while_held_sequence(RIGHTTRIGGER=0.1)
    .trigger(Axis.RIGHTTRIGGER, 1.0).wait_ms(15)
    .trigger(Axis.RIGHTTRIGGER, 0.0).wait_ms(15)
    .build()
```

---

## Advanced: `LOOP_LAST`

`LOOP_LAST` has no dedicated builder method and must be set manually via `MacroType`. It is like `LOOP` (toggle on press) but instead of looping, it runs the sequence **once** and then **holds the final state** until toggled off. Useful for "activate and stay" effects.

```python
from XSerialOne.macro_system import Macro, MacroType, ParallelAction, ActivationCondition
from XSerialOne import Button, Axis

steps = [
    ParallelAction(axis_changes={Axis.LEFTSTICKY: -1.0}, duration=0.5),
    ParallelAction(axis_changes={Axis.LEFTSTICKY: -0.5}),   # held here
]
macro = Macro(
    name="creep",
    steps=steps,
    activation_condition=ActivationCondition(buttons=[Button.LS]),
    macro_type=MacroType.LOOP_LAST,
)
```

---

## Output merging

When multiple macros are active at the same time, `MacroManager` merges their outputs:

- **Buttons:** OR-merged by priority: higher priority macros win conflicts.
- **Left stick / Right stick:** outputs are vector-summed then clamped to magnitude 1.0. A macro pushing `(0.5, 0)` and another pushing `(0, 0.5)` produce `(0.5, 0.5)` normalised.
- **Triggers and other axes:** last writer wins (highest priority).
- **D-pad:** last writer wins.

Set priority on a macro by passing `priority=` to the `Macro` constructor directly, or by subclassing.

---

## Quick reference

| Builder method | `build(loop=True)`? | Loops | Stops when |
|---|---|---|---|
| `activate_on_press` | No | No, runs once | Sequence completes |
| `activate_on_press` | Yes | Toggle loop | Pressed again |
| `activate_on_hold` | No | No, runs once | Sequence completes |
| `activate_on_combo` | No | No, runs once | Sequence completes |
| `activate_on_combo` | Yes | Toggle loop | Pressed again |
| `activate_on_double_tap` | No | No, runs once | Sequence completes |
| `activate_while_held_state` | N/A | No, holds last frame | Condition released |
| `activate_while_held_sequence` | N/A | Yes, while held | Condition released |
| `MacroType.LOOP_LAST` (manual) | N/A | No, holds last frame | Toggled off |
