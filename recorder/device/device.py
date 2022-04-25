from recorder.io import yaml_dump

from typing import Dict
from pathlib import Path
from datetime import datetime
from abc import ABC, ABCMeta, abstractmethod


class MetaDevice(ABCMeta):

    def __str__(cls) -> str:
        return cls.__name__

    def __repr__(cls) -> str:
        return cls.__name__.lower()


class Device(ABC, metaclass=MetaDevice):

    def __init__(self, index: int, output_folder: Path, config: dict):
        self.config = config
        assert 'start_timestamp' not in self.config
        assert 'end_timestamp' not in self.config
        self.index = index
        self.name = self.config.get('name', 'unknown')
        self.output_file = output_folder / f'{repr(self)}'

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f'{repr(type(self))}{self.index}'

    def __del__(self):
        yaml_dump(self.config, to_file=self.output_file.with_suffix('.yaml'))

    @classmethod
    @abstractmethod
    def find(cls) -> Dict[int, dict]:
        """Finds devices connected to the current system. 

        Returns:
            dict: A dictionary of devices with a numeric `id` as key and a
            the device properties as value.
        """
        pass

    def start(self) -> None:
        # Starts recording storing the start timestamp in configuration
        self.config['start_timestamp'] = datetime.now().timestamp()
        self._start()

    @abstractmethod
    def _start(self) -> None:
        # Starts recording.
        pass

    def stop(self):
        # Stops recording storing the end timestamp in configuration
        self._stop()
        self.config['end_timestamp'] = datetime.now().timestamp()

    @abstractmethod
    def _stop(self):
        # Stops recording
        pass

    @classmethod
    @abstractmethod
    def show_results(cls, from_folder):
        pass