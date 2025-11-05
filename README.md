# XSerialOne
The XSerialOne Framework is a Python library that provides a modular pipeline for generating and modifying simulated Xbox controller inputs through code, using my custom XSerialOne Hardware Device.

Unlike other on-market devices that rely on fixed-function hardware, such as just applying macros, the XSerialOne Framework interfaces the device and therefore console with a computer running the software pipeline.

This enables developers to construct interchangeable software modules that modify or generate input dynamically; for example, applying deadzones, reading input from a physical controller, integrating Twitch chat commands, or producing input from camera-based detection in realtime.

## Features
- Control Xbox Consoles enitrely with code using the XSerialOne hardware.
- Chain together input generators and modifiers to create complex behaviors.
- Custom modules can be built purely with Python code using the provided Base Classes, making customization of inputs limited only by your imagination.

## Disclaimer
- This project was started as an educational exercise in understanding console input systems and the ways in which they can be manipulated.
- In order to not promote cheating using such software, I will not publish any designs or information about the XSerialOne device.
- Users are responsible for complying with the terms of service of the platforms they use, I do not hold any responsbility for misuse of this software or hardware.

## Quick Setup

1. Install the package (currently in development mode):
```powershell
mkdir XSerialOneRepo
cd XSerialOneRepo
git clone https://github.com/Elisiah/XSerialOne.git .
pip install -e .
```

2. Run a script that uses the library:
```powershell
python examples/example.py
```

## Project Structure
```
XSerialOneRepo/
├── XSerialOne/          
│   ├── base.py          
│   ├── pipeline.py      
│   ├── serial_interface.py
│   ├── debug_viewer.py
│   └── modules/               # Generators and Modifiers
└── tests/               
└── examples/            
```

## Creating Custom Modules
This framework breaks down altering simulated inputs into two main components: Generators and Modifiers.

### Input Generators
A generator is a source of input data, such as reading from a controller or generating synthetic input.
```python
from XSerialOne.base import BaseGenerator, FrameState

class MyGenerator(BaseGenerator):
    def generate(self) -> FrameState:
        # Create a frame state with custom values
        return FrameState(
            buttons=(False,) * 10,     # 10 button states as tuple
            axes=(0.0,) * 6,          # 6 axes (LX,LY,RX,RY,LT,RT)
            dpad=(0, 0)               # dpad (x,y) each -1,0,1
        )
        
        # Or create from a dictionary
        return FrameState.from_dict({
            "buttons": [False] * 10,
            "axes": [0.0] * 6,
            "dpad": (0, 0)
        })
```

### Input Modifiers
A modifier processes and alters the input data from generators or states from a previous modifier.
```python
from XSerialOne.base import BaseModifier, FrameState

class MyModifier(BaseModifier):
    def update(self, state: FrameState) -> FrameState:
        # Convert state to mutable lists for modification
        buttons = list(state.buttons)
        axes = list(state.axes)
        dpad = list(state.dpad)
        
        # Modify values as needed
        axes[0] *= 1.5  # e.g., increase left stick X sensitivity
        
        # Return new immutable state
        return FrameState(
            buttons=tuple(buttons),
            axes=tuple(axes),
            dpad=tuple(dpad)
        )
```

### Using the Pipeline
```python
from XSerialOne.pipeline import InputPipeline
from XSerialOne.modules.xinput import XInputGenerator
from XSerialOne.debug_viewer import DebugViewer

# Create pipeline with optional serial port (XSerialOne Device)
pipeline = InputPipeline("COM3")  # or None for no serial output

# Add input source or generator
pipeline.add_generator(XInputGenerator())

# Add modifiers
pipeline.add_modifier(MyModifier())

# Optional: Add debug viewer
viewer = DebugViewer(show_second_screen=True)
viewer.attach_to_pipeline(pipeline)
viewer.start()

# Run the pipeline
try:
    pipeline.run_loop()
finally:
    if viewer:
        viewer.stop()
```

## Development

To run tests (once added):
```powershell
python -m pytest tests/
```