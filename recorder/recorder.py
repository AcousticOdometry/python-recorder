from recorder.config import Config, DEFAULT_OUTPUT_FOLDER
from recorder.io import yaml_dump

from time import sleep
from pathlib import Path
from typing import Optional
from typer import progressbar
from datetime import datetime


class Recorder:

    def __init__(
        self,
        config: Config,
        output_folder: Optional[Path] = DEFAULT_OUTPUT_FOLDER,
        # TODO paramters into output_folder name
        ):
        self.config = config
        output_folder.mkdir(parents=True, exist_ok=True)
        self.output_folder = output_folder / \
            datetime.now().strftime('date_%Y-%m-%d;time_%H-%M-%S')
        self.output_folder.mkdir(exist_ok=False)
        # Initialize all devices
        self.devices = self.config.devices(self.output_folder)

    def start(self):
        # Start the recording
        for d in self.devices:
            d.start()

    def stop(self):
        # Stop the recording
        for d in self.devices:
            d.stop()

    def wait(self, seconds: Optional[int] = None):
        # Wait for user input
        if seconds is None:
            input('Press `Enter` to stop recording.')
        else:
            with progressbar(range(seconds * 10), label='Recording...') as p:
                for _ in p:
                    sleep(0.1)

    def __call__(self, seconds: Optional[int] = None) -> Path:
        self.start()
        self.wait(seconds=seconds)
        self.stop()
        # Cleanup devices, a new instance of the recorder must be called
        del self.devices
        return self.output_folder