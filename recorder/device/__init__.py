from .device import Device
try:
    from .microphone import Microphone
except ImportError as e:
    class Microphone:
        def __init__(self, *args, **kwargs) -> None:
            raise e
try:
    from .realsense import RealSense
except ImportError as e:
    class RealSense:
        def __init__(self, *args, **kwargs) -> None:
            raise e

DEVICE_CLASSES = {repr(cls): cls for cls in Device.__subclasses__()}