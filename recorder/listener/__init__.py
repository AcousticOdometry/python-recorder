from .listener import Listener

try:
    from .localhost import Localhost
except ImportError as e:
    class Localhost:
        def __init__(self, *args, **kwargs) -> None:
            raise e

LISTENER_CLASSES = {repr(cls): cls for cls in Listener.__subclasses__()}