from recorder.config import Config, DEFAULT_OUTPUT_FOLDER

from time import sleep
from pathlib import Path
from copy import deepcopy
from typing import Optional
from typer import progressbar
from datetime import datetime


class Recorder:
    next_output = None
    devices = []

    def __init__(
        self,
        config: Config,
        output_folder: Optional[Path] = DEFAULT_OUTPUT_FOLDER,
        setup_name: Optional[str] = None,
        ):
        """Recorder object, used to record data from configured devices.

        Args:
            config (Config): Configuration dictionary.

            output_folder (Optional[Path]): Root folder for the recorded
                output. For each recording session, a subfolder will be created
                based on the `setup_name` provided. Defaults to
                DEFAULT_OUTPUT_FOLDER.
            setup_name (Optional[str]): The recorded output will be placed in a
                subfolder of `output_folder` with the provided name. If not
                provided, it will default to a name based on the current date
                and time. If `False` is provided instead, the recorder will not
                be fully initialized and an additionall call to `setup` will be
                required.
        """
        self.input_config = config
        self.config = deepcopy(self.input_config)
        # Initialize the output folder
        self.output_folder = output_folder
        self.output_folder.mkdir(parents=True, exist_ok=True)
        if setup_name is not False:
            self.setup(setup_name)
    
    def setup(self, name: Optional[str] = None, reset_config: bool = True):
        if reset_config:
            self.config = deepcopy(self.input_config)
        # Initialize next recording output
        if not name:
            name = datetime.now().strftime('date_%Y-%m-%d;time_%H-%M-%S')
        self.next_output = self.output_folder / name
        self.next_output.mkdir(exist_ok=False)
        # Initialize all devices
        self.devices = self.config.devices(self.next_output)

    def start(self):
        # Start the recording. Does nothing if the recording is not setup.
        for d in self.devices:
            d.start()

    def stop(self) -> Path:
        # Stop the recording
        for d in self.devices:
            d.stop()
        # Cleanup devices, setup must be called to start recording again
        self.devices = []
        if not self.next_output:
            raise RuntimeError('Recording not setup')
        output = Path(str(self.next_output))
        self.next_output = None
        return output

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
        return self.stop()