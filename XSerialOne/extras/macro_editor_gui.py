"""
macro_editor_gui.py
Author: Ellie V.

Visual macro editor GUI for XSerialOne sequences (inspired by TAS input makers).

Features:
- Click buttons to press/release
- Visual stick circles with clickable point placement
- Numeric input fields for precise stick/trigger control (-1.0 to 1.0)
- Polar input (angle + magnitude) for stick vectors
- Timing control
- Save/load sequences as JSON
"""

import math
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from XSerialOne.base import FrameState
from XSerialOne.frame_constants import Axis, Button
from XSerialOne.sequence import Sequence, SequenceFrame


class StickVisualizer(tk.Canvas):
    """Visual circle for stick input with clickable points and drag support."""
    
    def __init__(self, parent, width=200, height=200, on_change=None, **kwargs):
        super().__init__(parent, width=width, height=height, bg="#2b2b2b", 
                         highlightthickness=1, highlightbackground="#555555", **kwargs)
        self.width = width
        self.height = height
        self.center_x = width // 2
        self.center_y = height // 2
        self.radius = min(width, height) // 2 - 20
        self.on_change = on_change
        
        # Current stick position (-1.0 to 1.0)
        self.x = 0.0
        self.y = 0.0
        self.dragging = False
        
        # Bind events
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        
        self.draw()
    
    def draw(self):
        """Redraw the stick visualizer."""
        self.delete("all")
        
        # Background circle
        self.create_oval(
            self.center_x - self.radius, self.center_y - self.radius,
            self.center_x + self.radius, self.center_y + self.radius,
            outline="#444444", fill="#1a1a1a", width=2
        )
        
        # Crosshairs
        self.create_line(
            self.center_x - self.radius - 5, self.center_y,
            self.center_x + self.radius + 5, self.center_y,
            fill="#333333", width=1
        )
        self.create_line(
            self.center_x, self.center_y - self.radius - 5,
            self.center_x, self.center_y + self.radius + 5,
            fill="#333333", width=1
        )
        
        # Scale markers (-1.0, -0.5, 0.0, 0.5, 1.0)
        for value in [-1.0, -0.5, 0.0, 0.5, 1.0]:
            px = self.center_x + value * self.radius
            self.create_line(px, self.center_y - 3, px, self.center_y + 3, 
                           fill="#555555", width=1)
            py = self.center_y + value * self.radius
            self.create_line(self.center_x - 3, py, self.center_x + 3, py, 
                           fill="#555555", width=1)
        
        # Current position
        px = self.center_x + self.x * self.radius
        py = self.center_y - self.y * self.radius  # Invert Y for screen coords
        
        # Position vector line
        self.create_line(self.center_x, self.center_y, px, py, 
                        fill="#00ff00", width=2)
        
        # Position dot
        dot_size = 8
        self.create_oval(px - dot_size, py - dot_size, px + dot_size, py + dot_size,
                        fill="#00ff00", outline="#00ff00", width=2)
        
        # Coordinates label
        coord_text = f"({self.x:+.2f}, {self.y:+.2f})"
        mag = math.sqrt(self.x**2 + self.y**2)
        angle = math.degrees(math.atan2(self.y, self.x))
        polar_text = f"∠{angle:.0f}° r={mag:.2f}"
        
        self.create_text(self.center_x, 10, text=coord_text, fill="#00ff00", 
                        font=("Courier", 9))
        self.create_text(self.center_x, self.height - 10, text=polar_text, 
                        fill="#00ff00", font=("Courier", 9))
    
    def on_click(self, event):
        """Handle mouse click on canvas."""
        self.dragging = True
        self.update_position(event.x, event.y)
    
    def on_drag(self, event):
        """Handle mouse drag on canvas."""
        if self.dragging:
            self.update_position(event.x, event.y)
    
    def on_release(self, event):
        """Handle mouse release."""
        self.dragging = False
    
    def update_position(self, px, py):
        """Update stick position from pixel coordinates."""
        dx = px - self.center_x
        dy = -(py - self.center_y)  # Invert Y
        
        # Clamp to circle
        dist = math.sqrt(dx**2 + dy**2)
        if dist > self.radius:
            dx = (dx / dist) * self.radius
            dy = (dy / dist) * self.radius
        
        self.x = dx / self.radius
        self.y = dy / self.radius
        
        # Clamp to [-1.0, 1.0]
        self.x = max(-1.0, min(1.0, self.x))
        self.y = max(-1.0, min(1.0, self.y))
        
        self.draw()
        if self.on_change:
            self.on_change(self.x, self.y)
    
    def set_value(self, x: float, y: float):
        """Set stick position programmatically."""
        self.x = max(-1.0, min(1.0, x))
        self.y = max(-1.0, min(1.0, y))
        self.draw()
    
    def get_value(self):
        """Get current stick position."""
        return self.x, self.y


class MacroEditorGUI:
    """Visual macro editor for building input sequences (TAS-style)."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("XSerialOne Macro Editor - TAS Input Maker")
        self.root.geometry("1200x800")
        
        # Set dark theme
        style = ttk.Style()
        style.theme_use('clam')
        
        # Current sequence
        self.sequence = Sequence(name="Untitled", description="")
        self.current_frame_idx = 0
        self.current_frame_state = FrameState()
        
        # Setup UI
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the user interface."""
        # Top menu bar
        self.setup_menu()
        
        # Main content area
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left side: Frame editor
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.setup_frame_editor(left_frame)
        
        # Right side: Sequence timeline
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        self.setup_timeline(right_frame)
    
    def setup_menu(self):
        """Setup menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_sequence)
        file_menu.add_command(label="Open...", command=self.open_sequence)
        file_menu.add_command(label="Save", command=self.save_sequence)
        file_menu.add_command(label="Save As...", command=self.save_sequence_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Insert Frame Before", command=self.insert_frame_before)
        edit_menu.add_command(label="Insert Frame After", command=self.insert_frame_after)
        edit_menu.add_command(label="Delete Frame", command=self.delete_frame)
        edit_menu.add_separator()
        edit_menu.add_command(label="Clear All Frames", command=self.clear_frames)
    
    def setup_frame_editor(self, parent):
        """Setup the frame editor panel with visual stick circles and numeric input."""
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(title_frame, text="Frame Editor", font=("Arial", 14, "bold")).pack(anchor=tk.W)
        
        # Frame info section
        info_frame = ttk.LabelFrame(parent, text="Frame Info", padding=8)
        info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(info_frame, text="Current Frame:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.frame_idx_label = ttk.Label(info_frame, text="0", font=("Arial", 10, "bold"))
        self.frame_idx_label.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(info_frame, text="Timing (ms):").grid(row=0, column=2, sticky=tk.E, padx=5)
        self.timing_var = tk.StringVar(value="0")
        timing_entry = ttk.Entry(info_frame, textvariable=self.timing_var, width=10)
        timing_entry.grid(row=0, column=3, sticky=tk.W, padx=5)
        
        # Button panel
        button_frame = ttk.LabelFrame(parent, text="Buttons", padding=8)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.button_vars = {}
        button_names = [
            (Button.A, "A"), (Button.B, "B"), (Button.X, "X"), (Button.Y, "Y"),
            (Button.LB, "LB"), (Button.RB, "RB"),
            (Button.BACK, "Back"), (Button.START, "Start"),
            (Button.LS, "LS"), (Button.RS, "RS")
        ]
        
        for i, (btn, name) in enumerate(button_names):
            var = tk.BooleanVar()
            self.button_vars[btn] = var
            cb = ttk.Checkbutton(button_frame, text=name, variable=var)
            cb.grid(row=i//5, column=i%5, sticky=tk.W, padx=3, pady=3)
        
        # Analog sticks section
        sticks_frame = ttk.LabelFrame(parent, text="Analog Sticks (Range: -1.0 to 1.0)", padding=8)
        sticks_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Left stick
        left_label = ttk.Label(sticks_frame, text="Left Stick", font=("Arial", 11, "bold"))
        left_label.grid(row=0, column=0, sticky=tk.W, padx=5, columnspan=2)
        
        self.left_stick_viz = StickVisualizer(
            sticks_frame, width=200, height=200,
            on_change=self.on_left_stick_change
        )
        self.left_stick_viz.grid(row=1, column=0, padx=10, pady=5)
        
        # Left stick numeric input
        left_input_frame = ttk.Frame(sticks_frame)
        left_input_frame.grid(row=1, column=1, padx=10, pady=5, sticky=tk.N)
        
        ttk.Label(left_input_frame, text="X:", font=("Arial", 9)).grid(row=0, column=0, sticky=tk.W)
        self.left_stick_x_var = tk.StringVar(value="0.00")
        ttk.Entry(left_input_frame, textvariable=self.left_stick_x_var, width=8).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(left_input_frame, text="Y:", font=("Arial", 9)).grid(row=1, column=0, sticky=tk.W)
        self.left_stick_y_var = tk.StringVar(value="0.00")
        ttk.Entry(left_input_frame, textvariable=self.left_stick_y_var, width=8).grid(row=1, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(left_input_frame, text="Angle:", font=("Arial", 9)).grid(row=2, column=0, sticky=tk.W)
        self.left_stick_angle_var = tk.StringVar(value="0")
        ttk.Entry(left_input_frame, textvariable=self.left_stick_angle_var, width=8).grid(row=2, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(left_input_frame, text="Magnitude:", font=("Arial", 9)).grid(row=3, column=0, sticky=tk.W)
        self.left_stick_mag_var = tk.StringVar(value="0.00")
        ttk.Entry(left_input_frame, textvariable=self.left_stick_mag_var, width=8).grid(row=3, column=1, sticky=tk.W, padx=5)
        
        ttk.Button(left_input_frame, text="Apply Polar", 
                  command=self.apply_left_polar).grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=5)
        
        # Right stick
        right_label = ttk.Label(sticks_frame, text="Right Stick", font=("Arial", 11, "bold"))
        right_label.grid(row=0, column=2, sticky=tk.W, padx=5, columnspan=2)
        
        self.right_stick_viz = StickVisualizer(
            sticks_frame, width=200, height=200,
            on_change=self.on_right_stick_change
        )
        self.right_stick_viz.grid(row=1, column=2, padx=10, pady=5)
        
        # Right stick numeric input
        right_input_frame = ttk.Frame(sticks_frame)
        right_input_frame.grid(row=1, column=3, padx=10, pady=5, sticky=tk.N)
        
        ttk.Label(right_input_frame, text="X:", font=("Arial", 9)).grid(row=0, column=0, sticky=tk.W)
        self.right_stick_x_var = tk.StringVar(value="0.00")
        ttk.Entry(right_input_frame, textvariable=self.right_stick_x_var, width=8).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(right_input_frame, text="Y:", font=("Arial", 9)).grid(row=1, column=0, sticky=tk.W)
        self.right_stick_y_var = tk.StringVar(value="0.00")
        ttk.Entry(right_input_frame, textvariable=self.right_stick_y_var, width=8).grid(row=1, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(right_input_frame, text="Angle:", font=("Arial", 9)).grid(row=2, column=0, sticky=tk.W)
        self.right_stick_angle_var = tk.StringVar(value="0")
        ttk.Entry(right_input_frame, textvariable=self.right_stick_angle_var, width=8).grid(row=2, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(right_input_frame, text="Magnitude:", font=("Arial", 9)).grid(row=3, column=0, sticky=tk.W)
        self.right_stick_mag_var = tk.StringVar(value="0.00")
        ttk.Entry(right_input_frame, textvariable=self.right_stick_mag_var, width=8).grid(row=3, column=1, sticky=tk.W, padx=5)
        
        ttk.Button(right_input_frame, text="Apply Polar", 
                  command=self.apply_right_polar).grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=5)
        
        # Triggers
        triggers_frame = ttk.LabelFrame(parent, text="Triggers (Range: -1.0 to 1.0)", padding=8)
        triggers_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(triggers_frame, text="Left Trigger:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.left_trigger_var = tk.StringVar(value="0.00")
        ttk.Entry(triggers_frame, textvariable=self.left_trigger_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5)
        self.left_trigger_scale = tk.Scale(triggers_frame, from_=-1.0, to=1.0, orient=tk.HORIZONTAL, 
                                           resolution=0.01, command=self.on_left_trigger_change)
        self.left_trigger_scale.set(0)
        self.left_trigger_scale.grid(row=0, column=2, sticky=tk.EW, padx=5)
        
        ttk.Label(triggers_frame, text="Right Trigger:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.right_trigger_var = tk.StringVar(value="0.00")
        ttk.Entry(triggers_frame, textvariable=self.right_trigger_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5)
        self.right_trigger_scale = tk.Scale(triggers_frame, from_=-1.0, to=1.0, orient=tk.HORIZONTAL,
                                            resolution=0.01, command=self.on_right_trigger_change)
        self.right_trigger_scale.set(0)
        self.right_trigger_scale.grid(row=1, column=2, sticky=tk.EW, padx=5)
        
        triggers_frame.columnconfigure(2, weight=1)
        
        # Action buttons
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(action_frame, text="Add Frame", command=self.add_frame).pack(side=tk.LEFT, padx=3)
        ttk.Button(action_frame, text="Update Frame", command=self.update_frame).pack(side=tk.LEFT, padx=3)
        ttk.Button(action_frame, text="Clear Frame", command=self.clear_frame).pack(side=tk.LEFT, padx=3)
    
    def setup_timeline(self, parent):
        """Setup the sequence timeline panel."""
        ttk.Label(parent, text="Sequence Timeline", font=("Arial", 12, "bold")).pack(anchor=tk.W)
        
        # Sequence info
        info_frame = ttk.LabelFrame(parent, text="Sequence Info", padding=5)
        info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(info_frame, text="Name:").grid(row=0, column=0, sticky=tk.W)
        self.seq_name_var = tk.StringVar(value="Untitled")
        ttk.Entry(info_frame, textvariable=self.seq_name_var).grid(row=0, column=1, sticky=tk.EW)
        
        ttk.Label(info_frame, text="Description:").grid(row=1, column=0, sticky=tk.W)
        self.seq_desc_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.seq_desc_var).grid(row=1, column=1, sticky=tk.EW)
        
        ttk.Label(info_frame, text="Frames:").grid(row=2, column=0, sticky=tk.W)
        self.frame_count_label = ttk.Label(info_frame, text="0")
        self.frame_count_label.grid(row=2, column=1, sticky=tk.W)
        
        ttk.Label(info_frame, text="Duration (ms):").grid(row=3, column=0, sticky=tk.W)
        self.duration_label = ttk.Label(info_frame, text="0")
        self.duration_label.grid(row=3, column=1, sticky=tk.W)
        
        # Frame list
        list_frame = ttk.LabelFrame(parent, text="Frames", padding=5)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Listbox
        self.frame_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.frame_listbox.pack(fill=tk.BOTH, expand=True)
        self.frame_listbox.bind('<<ListboxSelect>>', self.on_frame_selected)
        scrollbar.config(command=self.frame_listbox.yview)
    
    def get_current_frame_state(self) -> FrameState:
        """Get the current frame state from UI controls."""
        buttons = [False] * 10
        for btn, var in self.button_vars.items():
            buttons[btn.value] = var.get()
        
        # Get stick values from visualizers
        left_x, left_y = self.left_stick_viz.get_value()
        right_x, right_y = self.right_stick_viz.get_value()
        
        # Get trigger values
        try:
            left_trig = float(self.left_trigger_var.get())
            right_trig = float(self.right_trigger_var.get())
        except ValueError:
            left_trig = self.left_trigger_scale.get()
            right_trig = self.right_trigger_scale.get()
        
        axes = [
            left_x,
            left_y,
            right_x,
            right_y,
            left_trig,
            right_trig,
        ]
        
        return FrameState(buttons=tuple(buttons), axes=tuple(axes), dpad=(0, 0))
    
    def set_frame_state(self, frame: FrameState):
        """Set the UI controls from a frame state."""
        # Buttons
        for btn, var in self.button_vars.items():
            var.set(frame.buttons[btn.value])
        
        # Sticks from visualizers
        self.left_stick_viz.set_value(frame.axes[Axis.LEFTSTICKX], frame.axes[Axis.LEFTSTICKY])
        self.right_stick_viz.set_value(frame.axes[Axis.RIGHTSTICKX], frame.axes[Axis.RIGHTSTICKY])
        
        # Triggers
        self.left_trigger_var.set(f"{frame.axes[Axis.LEFTTRIGGER]:.2f}")
        self.left_trigger_scale.set(frame.axes[Axis.LEFTTRIGGER])
        self.right_trigger_var.set(f"{frame.axes[Axis.RIGHTTRIGGER]:.2f}")
        self.right_trigger_scale.set(frame.axes[Axis.RIGHTTRIGGER])
        
        self.update_stick_display()
    
    def on_left_stick_change(self, x: float, y: float):
        """Callback when left stick is changed."""
        self.left_stick_x_var.set(f"{x:.2f}")
        self.left_stick_y_var.set(f"{y:.2f}")
        mag = math.sqrt(x**2 + y**2)
        angle = math.degrees(math.atan2(y, x))
        self.left_stick_mag_var.set(f"{mag:.2f}")
        self.left_stick_angle_var.set(f"{angle:.0f}")
    
    def on_right_stick_change(self, x: float, y: float):
        """Callback when right stick is changed."""
        self.right_stick_x_var.set(f"{x:.2f}")
        self.right_stick_y_var.set(f"{y:.2f}")
        mag = math.sqrt(x**2 + y**2)
        angle = math.degrees(math.atan2(y, x))
        self.right_stick_mag_var.set(f"{mag:.2f}")
        self.right_stick_angle_var.set(f"{angle:.0f}")
    
    def on_left_trigger_change(self, value):
        """Callback when left trigger slider changes."""
        self.left_trigger_var.set(f"{float(value):.2f}")
    
    def on_right_trigger_change(self, value):
        """Callback when right trigger slider changes."""
        self.right_trigger_var.set(f"{float(value):.2f}")
    
    def apply_left_polar(self):
        """Apply polar (angle + magnitude) input for left stick."""
        try:
            angle = math.radians(float(self.left_stick_angle_var.get()))
            mag = float(self.left_stick_mag_var.get())
            x = mag * math.cos(angle)
            y = mag * math.sin(angle)
            self.left_stick_viz.set_value(x, y)
            self.on_left_stick_change(x, y)
        except ValueError:
            messagebox.showerror("Error", "Invalid angle or magnitude value")
    
    def apply_right_polar(self):
        """Apply polar (angle + magnitude) input for right stick."""
        try:
            angle = math.radians(float(self.right_stick_angle_var.get()))
            mag = float(self.right_stick_mag_var.get())
            x = mag * math.cos(angle)
            y = mag * math.sin(angle)
            self.right_stick_viz.set_value(x, y)
            self.on_right_stick_change(x, y)
        except ValueError:
            messagebox.showerror("Error", "Invalid angle or magnitude value")
    
    def update_stick_display(self):
        """Update stick numeric displays from visualizers."""
        left_x, left_y = self.left_stick_viz.get_value()
        self.on_left_stick_change(left_x, left_y)
        
        right_x, right_y = self.right_stick_viz.get_value()
        self.on_right_stick_change(right_x, right_y)
    
    def add_frame(self):
        """Add current frame state to sequence."""
        try:
            timing = float(self.timing_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid timing value")
            return
        
        frame_state = self.get_current_frame_state()
        
        from XSerialOne.sequence import SequenceFrame
        self.sequence.frames.append(SequenceFrame(timing, frame_state.to_dict()))
        self.sequence.duration_ms = timing
        
        self.update_timeline()
        messagebox.showinfo("Success", "Frame added!")
    
    def update_frame(self):
        """Update the currently selected frame."""
        if self.current_frame_idx >= len(self.sequence.frames):
            messagebox.showerror("Error", "No frame selected")
            return
        
        try:
            timing = float(self.timing_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid timing value")
            return
        
        frame_state = self.get_current_frame_state()
        
        self.sequence.frames[self.current_frame_idx] = SequenceFrame(timing, frame_state.to_dict())
        
        self.update_timeline()
    
    def delete_frame(self):
        """Delete the currently selected frame."""
        if self.current_frame_idx >= len(self.sequence.frames):
            messagebox.showerror("Error", "No frame selected")
            return
        
        del self.sequence.frames[self.current_frame_idx]
        self.update_timeline()
    
    def insert_frame_before(self):
        """Insert a frame before the current one."""
        frame_state = self.get_current_frame_state()
        timing = float(self.timing_var.get()) if self.timing_var.get() else 0
        
        from XSerialOne.sequence import SequenceFrame
        self.sequence.frames.insert(self.current_frame_idx, SequenceFrame(timing, frame_state.to_dict()))
        self.update_timeline()
    
    def insert_frame_after(self):
        """Insert a frame after the current one."""
        frame_state = self.get_current_frame_state()
        timing = float(self.timing_var.get()) if self.timing_var.get() else 0
        
        from XSerialOne.sequence import SequenceFrame
        self.sequence.frames.insert(self.current_frame_idx + 1, SequenceFrame(timing, frame_state.to_dict()))
        self.update_timeline()
    
    def clear_frame(self):
        """Clear all controls."""
        for var in self.button_vars.values():
            var.set(False)
        self.left_stick_x.set(0)
        self.left_stick_y.set(0)
        self.right_stick_x.set(0)
        self.right_stick_y.set(0)
        self.left_trigger.set(0)
        self.right_trigger.set(0)
        self.timing_var.set("0")
    
    def clear_frames(self):
        """Clear all frames from sequence."""
        if messagebox.askyesno("Confirm", "Clear all frames?"):
            self.sequence.frames = []
            self.update_timeline()
    
    def on_frame_selected(self, event):
        """Handle frame selection from listbox."""
        selection = self.frame_listbox.curselection()
        if selection:
            self.current_frame_idx = selection[0]
            frame = self.sequence.frames[self.current_frame_idx]
            
            self.timing_var.set(str(int(frame.timestamp_ms)))
            self.set_frame_state(FrameState.from_dict(frame.frame))
            self.frame_idx_label.config(text=str(self.current_frame_idx))
    
    def update_timeline(self):
        """Refresh the timeline display."""
        self.frame_listbox.delete(0, tk.END)
        
        for i, frame in enumerate(self.sequence.frames):
            label = f"Frame {i}: {int(frame.timestamp_ms)}ms"
            self.frame_listbox.insert(tk.END, label)
        
        self.frame_count_label.config(text=str(len(self.sequence.frames)))
        self.duration_label.config(text=f"{int(self.sequence.duration_ms)}")
    
    def new_sequence(self):
        """Create new sequence."""
        self.sequence = Sequence(name="Untitled", description="")
        self.seq_name_var.set("Untitled")
        self.seq_desc_var.set("")
        self.update_timeline()
    
    def open_sequence(self):
        """Open sequence from file."""
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            self.sequence = Sequence.load(filepath)
            self.seq_name_var.set(self.sequence.name)
            self.seq_desc_var.set(self.sequence.description)
            self.update_timeline()
    
    def save_sequence(self):
        """Save sequence to file."""
        if not self.sequence.name or self.sequence.name == "Untitled":
            self.save_sequence_as()
            return
        
        # Try to save with existing filename
        filepath = f"{self.sequence.name}.json"
        self.sequence.name = self.seq_name_var.get()
        self.sequence.description = self.seq_desc_var.get()
        self.sequence.save(filepath)
        messagebox.showinfo("Success", f"Saved to {filepath}")
    
    def save_sequence_as(self):
        """Save sequence to new file."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filepath:
            self.sequence.name = self.seq_name_var.get()
            self.sequence.description = self.seq_desc_var.get()
            self.sequence.save(filepath)
            messagebox.showinfo("Success", f"Saved to {filepath}")


def main():
    """Launch the macro editor."""
    root = tk.Tk()
    _editor = MacroEditorGUI(root)  # keep ref to prevent GC
    root.mainloop()


if __name__ == "__main__":
    main()
