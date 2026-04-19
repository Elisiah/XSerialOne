# macro_builder_fixed.py
from XSerialOne.frame_constants import Axis, Dpad
from XSerialOne.macro_system import ActivationCondition, Macro, MacroType, ParallelAction


class MacroBuilder:
    """Fluid interface for building macros with all activation types"""
    def __init__(self, name: str):
        self.name = name
        self.steps = []
        self.current_step = ParallelAction()
        self.activation_buttons = []
        self.activation_dpad = None
        self.activation_triggers = {}
        self.activation_hold_duration = 0.0
        self.macro_type = MacroType.ON_PRESS
        
    def press(self, *buttons) -> 'MacroBuilder':
        """Press one or more buttons simultaneously"""
        for button in buttons:
            self.current_step.button_changes[button] = True
        return self
        
    def release(self, *buttons) -> 'MacroBuilder':
        """Release one or more buttons simultaneously"""
        for button in buttons:
            self.current_step.button_changes[button] = False
        return self
        
    def stick(self, axis: Axis, value: float) -> 'MacroBuilder':
        """Set stick position"""
        self.current_step.axis_changes[axis] = value
        return self
        
    def trigger(self, trigger: Axis, value: float) -> 'MacroBuilder':
        """Set trigger position"""
        self.current_step.axis_changes[trigger] = value
        return self
        
    def wait(self, seconds: float) -> 'MacroBuilder':
        """Complete current step and wait"""
        self.current_step.duration = seconds
        self.steps.append(self.current_step)
        self.current_step = ParallelAction()  # Start fresh step
        return self
        
    def wait_ms(self, milliseconds: float) -> 'MacroBuilder':
        """Wait specified milliseconds"""
        return self.wait(milliseconds / 1000.0)
    
    def activate_on_press(self, *buttons, dpad: Dpad = None, **triggers) -> 'MacroBuilder':
        """Activate on button press (rising edge)"""
        self.activation_buttons = list(buttons)
        self.activation_dpad = dpad
        self.activation_triggers = triggers
        self.macro_type = MacroType.ON_PRESS
        return self
        
    def activate_on_hold(self, *buttons, hold_ms: float = 500, dpad: Dpad = None, **triggers) -> 'MacroBuilder':
        """Activate after holding for specified time"""
        self.activation_buttons = list(buttons)
        self.activation_dpad = dpad
        self.activation_triggers = triggers
        self.activation_hold_duration = hold_ms / 1000.0
        self.macro_type = MacroType.ON_HOLD
        return self
        
    def activate_on_combo(self, *buttons, dpad: Dpad = None, **triggers) -> 'MacroBuilder':
        """Activate on button combination"""
        self.activation_buttons = list(buttons)
        self.activation_dpad = dpad
        self.activation_triggers = triggers
        self.macro_type = MacroType.ON_COMBO
        return self
        
    def activate_on_double_tap(self, *buttons, dpad: Dpad = None, **triggers) -> 'MacroBuilder':
        """Activate on double tap (within 300ms)"""
        self.activation_buttons = list(buttons)
        self.activation_dpad = dpad
        self.activation_triggers = triggers
        self.macro_type = MacroType.ON_DOUBLE_TAP
        return self
        
    def activate_while_held_state(self, *buttons, dpad: Dpad = None, **triggers) -> 'MacroBuilder':
        """Run sequence once, then hold final state while condition is met"""
        self.activation_buttons = list(buttons)
        self.activation_dpad = dpad
        self.activation_triggers = triggers
        self.macro_type = MacroType.WHILE_HELD_STATE
        return self
        
    def activate_while_held_sequence(self, *buttons, dpad: Dpad = None, **triggers) -> 'MacroBuilder':
        """Repeat sequence while condition is met"""
        self.activation_buttons = list(buttons)
        self.activation_dpad = dpad
        self.activation_triggers = triggers
        self.macro_type = MacroType.WHILE_HELD_SEQUENCE
        return self
        
    def build(self, loop: bool = False) -> Macro:
        # Add the last step if it has actions
        if self.current_step.button_changes or self.current_step.axis_changes:
            self.steps.append(self.current_step)
            
        # Handle loop behavior - overrides macro type for LOOP
        if loop:
            self.macro_type = MacroType.LOOP
            
        # Create activation condition
        activation_condition = None
        if self.activation_buttons or self.activation_dpad or self.activation_triggers:
            trigger_conditions = {}
            for trigger_name, threshold in self.activation_triggers.items():
                if isinstance(trigger_name, str):
                    trigger_conditions[getattr(Axis, trigger_name.upper())] = threshold
                else:
                    trigger_conditions[trigger_name] = threshold
                    
            activation_condition = ActivationCondition(
                buttons=self.activation_buttons,
                dpad=self.activation_dpad,
                triggers=trigger_conditions,
                hold_duration=self.activation_hold_duration
            )
            
        macro = Macro(self.name, self.steps, activation_condition, self.macro_type)
        return macro