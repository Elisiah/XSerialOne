# xserial_constants.py
"""
frame_constants.py

Helper enums and constants for frame axis, button, and dpad direction indexing.
"""

from enum import IntEnum

class Axis(IntEnum):
    LEFTSTICKX = 0
    LEFTSTICKY = 1
    RIGHTSTICKX = 2
    RIGHTSTICKY = 3
    LEFTTRIGGER = 4
    RIGHTTRIGGER = 5

class Button(IntEnum):
    A = 0
    B = 1
    X = 2
    Y = 3
    LB = 4
    RB = 5
    BACK = 6
    START = 7
    LS = 8
    RS = 9

class Dpad:
    CENTER = (0, 0)
    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)
    UPLEFT = (-1, 1)
    UPRIGHT = (1, 1)
    DOWNLEFT = (-1, -1)
    DOWNRIGHT = (1, -1)
