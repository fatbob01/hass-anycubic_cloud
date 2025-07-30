"""Constants for Anycubic Cloud API helpers."""
from enum import IntEnum

class AnycubicOrderID(IntEnum):
    CAMERA_OPEN = 1001  # start cloud stream
    CAMERA_CLOSE = 1002  # stop  cloud stream
