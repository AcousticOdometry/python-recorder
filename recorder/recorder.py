from recorder.settings import DEFAULT_OUTPUT_FOLDER
from recorder.device import Device

from pathlib import Path
from typing import Optional, List


class Recorder:

    def __init__(
        devices: List[Device],
        output_folder: Optional[Path] = DEFAULT_OUTPUT_FOLDER,
        ):
        self.devices = devices
        self.output_folder = output_folder

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
        input('Press `Enter` to stop recording.')
    
    def __call__(self, seconds: Optional[int] = None):
        self.start()
        self.wait()
        self.stop()