import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from XSerialOne.base import FrameState
from XSerialOne.frame_constants import Axis, Button, Dpad


class MacroType(Enum):
    LOOP = "loop"
    LOOP_LAST = "loop_last"
    WHILE_HELD_STATE = "while_held_state"
    WHILE_HELD_SEQUENCE = "while_held_sequence"
    ON_PRESS = "on_press"
    ON_HOLD = "on_hold"
    ON_COMBO = "on_combo"
    ON_DOUBLE_TAP = "on_double_tap"

class MacroState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    RUNNING_HOLDING = "running_holding"
    COMPLETED = "completed"

@dataclass
class MacroOutput:
    buttons: Dict[Button, bool]
    axes: Dict[Axis, float]
    dpad: Optional[Dpad] = None
    priority: int = 0
    owned_axes: List[Axis] = None

    def __post_init__(self):
        if self.buttons is None:
            self.buttons = {}
        if self.axes is None:
            self.axes = {}
        if self.owned_axes is None:
            self.owned_axes = []

@dataclass
class ParallelAction:
    button_changes: Dict[Button, bool] = None
    axis_changes: Dict[Axis, float] = None
    duration: float = 0.0

    def __post_init__(self):
        if self.button_changes is None:
            self.button_changes = {}
        if self.axis_changes is None:
            self.axis_changes = {}

class ActivationCondition:
    def __init__(self, buttons: List[Button] = None, dpad: Dpad = None,
                 triggers: Dict[Axis, float] = None, hold_duration: float = 0.0):
        self.buttons = buttons or []
        self.dpad = dpad
        self.triggers = triggers or {}
        self.hold_duration = hold_duration

    def is_met(self, state: FrameState) -> bool:
        for button in self.buttons:
            if not state.buttons[button.value]:
                return False
        if self.dpad is not None and state.dpad != self.dpad:
            return False
        for trigger, threshold in self.triggers.items():
            if state.axes[trigger.value] < threshold:
                return False
        return True

class Macro:
    def __init__(self, name: str, steps: List[ParallelAction],
                 activation_condition: Optional[ActivationCondition] = None,
                 macro_type: MacroType = MacroType.ON_PRESS,
                 priority: int = 0,
                 owned_axes: Optional[List[Axis]] = None):
        self.name = name
        self.steps = steps
        self.activation_condition = activation_condition
        self.macro_type = macro_type
        self.priority = priority
        self.owned_axes = owned_axes or []

        self.current_step = 0
        self.step_start_time = 0.0
        self.state = MacroState.IDLE
        self.activation_start_time = 0.0
        self.last_activation_time = 0.0
        self.was_activated = False
        self.activation_count = 0
        self.final_state_output: Optional[MacroOutput] = None
        self.last_toggle_check = 0.0

    def should_activate(self, state: FrameState, current_time: float) -> bool:
        if not self.activation_condition:
            return False

        condition_met = self.activation_condition.is_met(state)
        if current_time - self.last_toggle_check < 0.1:
            return False
        self.last_toggle_check = current_time

        if self.macro_type in (MacroType.LOOP, MacroType.LOOP_LAST,
                               MacroType.WHILE_HELD_STATE, MacroType.WHILE_HELD_SEQUENCE):
            if condition_met and not self.was_activated:
                self.was_activated = True
                return True
            elif not condition_met:
                self.was_activated = False
                if self.state != MacroState.IDLE and self.macro_type in (MacroType.WHILE_HELD_STATE, MacroType.WHILE_HELD_SEQUENCE):
                    self.stop()
            return False

        if self.macro_type == MacroType.ON_PRESS:
            should = condition_met and not self.was_activated
            self.was_activated = condition_met
            return should

        if self.macro_type == MacroType.ON_HOLD:
            if condition_met and not self.was_activated:
                self.activation_start_time = current_time
                self.was_activated = True
            elif condition_met and self.was_activated:
                if current_time - self.activation_start_time >= self.activation_condition.hold_duration:
                    self.was_activated = False
                    return True
            else:
                self.was_activated = False
            return False

        if self.macro_type == MacroType.ON_DOUBLE_TAP:
            if condition_met and not self.was_activated:
                if current_time - self.last_activation_time < 0.3:
                    self.activation_count = 0
                    self.last_activation_time = 0
                    return True
                else:
                    self.activation_count = 1
                    self.last_activation_time = current_time
                    self.was_activated = True
            elif not condition_met:
                self.was_activated = False
            return False

        if self.macro_type == MacroType.ON_COMBO:
            should = condition_met and not self.was_activated
            self.was_activated = condition_met
            return should

        return False

    def start(self, start_time: Optional[float] = None):
        t = start_time if start_time is not None else time.perf_counter()
        self.current_step = 0
        self.step_start_time = t
        self.state = MacroState.RUNNING
        self.final_state_output = None

    def stop(self):
        if self.state != MacroState.IDLE:
            self.state = MacroState.IDLE
            self.was_activated = False
            self.final_state_output = None

    def toggle(self):
        if self.state == MacroState.IDLE:
            self.start()
        else:
            self.stop()

    def _current_step_action(self) -> Optional[ParallelAction]:
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    def update(self, current_time: float, input_state: FrameState) -> Optional[MacroOutput]:
        if self.state == MacroState.IDLE:
            return None

        if self.macro_type in (MacroType.WHILE_HELD_STATE, MacroType.WHILE_HELD_SEQUENCE):
            if self.activation_condition and not self.activation_condition.is_met(input_state):
                self.stop()
                return None

        if self.current_step >= len(self.steps):
            if self.macro_type in (MacroType.WHILE_HELD_STATE, MacroType.WHILE_HELD_SEQUENCE):
                if not self.activation_condition.is_met(input_state):
                    self.stop()
                    return None

            if self.macro_type in (MacroType.LOOP, MacroType.WHILE_HELD_SEQUENCE):
                self.current_step = 0
                self.step_start_time = current_time
            elif self.macro_type in (MacroType.LOOP_LAST, MacroType.WHILE_HELD_STATE):
                last_action = self.steps[-1] if self.steps else None
                out = self._action_to_output(last_action)
                self.state = MacroState.RUNNING_HOLDING
                self.final_state_output = out
                return out
            else:
                self.state = MacroState.COMPLETED
                return None

        action = self._current_step_action()
        if action is None:
            self.state = MacroState.COMPLETED
            return None

        elapsed = current_time - self.step_start_time
        output = self._action_to_output(action)

        if elapsed >= action.duration:
            self.current_step += 1
            self.step_start_time = current_time

        return output

    def _action_to_output(self, action: ParallelAction) -> MacroOutput:
        buttons = dict(action.button_changes) if action.button_changes else {}
        axes = dict(action.axis_changes) if action.axis_changes else {}
        return MacroOutput(buttons=buttons, axes=axes, dpad=None, priority=self.priority, owned_axes=list(self.owned_axes))

class MacroManager:
    def __init__(self):
        self.macros: Dict[str, Macro] = {}
        self.left_axes = (Axis.LEFTSTICKX, Axis.LEFTSTICKY)
        self.right_axes = (Axis.RIGHTSTICKX, Axis.RIGHTSTICKY)

    def register_macro(self, macro: Macro):
        if macro.name in self.macros and self.macros[macro.name].state != MacroState.IDLE:
            return
        self.macros[macro.name] = macro

    def run(self, name: str):
        macro = self.macros.get(name)
        if macro:
            macro.start(time.perf_counter())

    def stop(self, name: str):
        macro = self.macros.get(name)
        if macro:
            macro.stop()

    def toggle(self, name: str):
        macro = self.macros.get(name)
        if macro:
            macro.toggle()

    def _check_input_activations(self, input_state: FrameState, now: float):
        for macro in self.macros.values():
            try:
                if macro.should_activate(input_state, now):
                    if macro.macro_type in (MacroType.LOOP, MacroType.LOOP_LAST):
                        if macro.state == MacroState.RUNNING:
                            macro.stop()
                        else:
                            for other in self.macros.values():
                                if other is not macro and other.macro_type in (MacroType.LOOP, MacroType.LOOP_LAST) and other.state == MacroState.RUNNING:
                                    other.stop()
                            macro.start(now)
                    else:
                        macro.start(now)
            except Exception:
                pass

    def update(self, now: float, input_state: FrameState) -> FrameState:
        self._check_input_activations(input_state, now)
        outputs: List[MacroOutput] = []
        for macro in self.macros.values():
            out = macro.update(now, input_state)
            if out:
                outputs.append(out)

        if not outputs:
            return input_state

        outputs.sort(key=lambda o: o.priority)
        axes = list(input_state.axes)
        buttons = list(input_state.buttons)
        dpad = input_state.dpad

        for out in outputs:
            for btn, val in out.buttons.items():
                buttons[btn.value] = val

        for out in outputs:
            if out.dpad is not None:
                dpad = out.dpad

        def accumulate_stick(axes_pair: Tuple[Axis, Axis]) -> Tuple[float, float]:
            ax_sum, ay_sum = 0.0, 0.0
            for out in outputs:
                if out.owned_axes and not (axes_pair[0] in out.owned_axes or axes_pair[1] in out.owned_axes):
                    continue
                ax_sum += out.axes.get(axes_pair[0], 0.0)
                ay_sum += out.axes.get(axes_pair[1], 0.0)
            mag = math.hypot(ax_sum, ay_sum)
            if mag > 1.0:
                ax_sum /= mag
                ay_sum /= mag
            return ax_sum, ay_sum

        lx, ly = accumulate_stick(self.left_axes)
        if abs(lx) > 1e-6 or abs(ly) > 1e-6:
            axes[self.left_axes[0].value] = lx
            axes[self.left_axes[1].value] = ly

        rx, ry = accumulate_stick(self.right_axes)
        if abs(rx) > 1e-6 or abs(ry) > 1e-6:
            axes[self.right_axes[0].value] = rx
            axes[self.right_axes[1].value] = ry

        for axis in Axis:
            if axis in self.left_axes + self.right_axes:
                continue
            chosen = None
            for out in outputs:
                if axis in out.axes:
                    chosen = out.axes[axis]
            if chosen is not None:
                axes[axis.value] = chosen

        return FrameState(buttons=tuple(buttons), axes=tuple(axes), dpad=dpad)
