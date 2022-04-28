from recorder.io import yaml_dump, yaml_load
from recorder.device import Device, DEVICE_CLASSES

from typing import List
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.cwd() / 'python-recorder.yaml'

DEFAULT_OUTPUT_FOLDER = Path.cwd() / 'recordings'


class Config(dict):

    @classmethod
    def from_yaml(cls, path: Path = DEFAULT_CONFIG_PATH) -> 'Config':
        if not path.exists():
            raise AttributeError(f'Configuration file {path} does not exist')
        return cls(yaml_load(path))

    def devices(
        self,
        output_folder: Path = DEFAULT_OUTPUT_FOLDER,
        ) -> List[Device]:
        """Initializes all devices present in the dictionary with the provided
        output folder.

        Args:
            output_folder (Path, optional): Devices output_folder. Defaults to
            DEFAULT_OUTPUT_FOLDER.

        Raises:
            RuntimeError: _description_

        Returns:
            List[Device]: List of initialized devices.

        """
        devices = []
        for _device_class, _devices in self.items():
            try:
                device_class = DEVICE_CLASSES[_device_class]
            except KeyError:
                raise RuntimeError(
                    f'Invalid configuration file, {_device_class} is not a '
                    'valid device class. Available options: '
                    f'{list(DEVICE_CLASSES.keys())}'
                    )
            for index, device_config in _devices.items():
                try:
                    devices.append(
                        device_class(
                            index=index,
                            output_folder=output_folder,
                            config=device_config,
                            )
                        )
                except Exception as e:
                    raise RuntimeError(
                        f"Could not initialize {str(device_class)} {index} "
                        f"with config:\n{yaml_dump(device_config)}\n{str(e)}"
                        ) from e
        return devices
