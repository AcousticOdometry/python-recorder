from recorder import Recorder
from abc import ABC, ABCMeta, abstractmethod


class MetaListener(ABCMeta):

    def __str__(cls) -> str:
        return cls.__name__

    def __repr__(cls) -> str:
        return cls.__name__.lower()

class Listener(ABC, metaclass=MetaListener):

    def __init__(self, recorder: Recorder) -> None:
        self.recorder = recorder

    @abstractmethod
    def listen(self) -> None:
        pass