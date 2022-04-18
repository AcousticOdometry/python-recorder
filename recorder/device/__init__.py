from .device import Device
from .microphone import Microphone
from .realsense import RealSense

DEVICE_CLASSES = {repr(cls): cls for cls in Device.__subclasses__()}