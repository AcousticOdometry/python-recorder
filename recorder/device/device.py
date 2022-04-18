from typing import Dict
from pathlib import Path
from abc import ABC, ABCMeta, abstractmethod


class MetaDevice(ABCMeta):

    def __str__(cls):
        return cls.__name__


class Device(ABC, metaclass=MetaDevice):

    def __init__(self, _index: int, output_folder: Path, *args, **kwargs):
        self.name = kwargs.get('name', 'unknown')
        self.output_file = output_folder / f'{self.__name__.lower()}{_index}'

    def __str__(self) -> str:
        return self.name

    @classmethod
    @abstractmethod
    def find(cls) -> Dict[int, dict]:
        """Finds devices connected to the current system. 

        Returns:
            dict: A dictionary of devices with a numeric `id` as key and a
            the device properties as value.
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """Starts recording.

        Returns:
            None
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops recording.

        Returns:
            None
        """
        pass
