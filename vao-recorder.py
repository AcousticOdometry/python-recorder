"""
Record visual and acoustic data from the connected devices. It allows
interaction with microphones, cameras and RealSense devices.

Workflow: Configure the devices to be used. One can always modify the
configuration manually in the generated `yaml` file.

>>> python vao-recorder.py config

Test that the chosen audio devices are working

>>> python vao-recorder.py test-microphones

Record an experiment with the chosen devices

>>> python vao-recorder.py record
"""
import pyrealsense2 as rs
import sounddevice as sd
import numpy as np
import typer
import yaml
import wave
# import cv2

from typing import Optional, Tuple, Callable
from abc import ABC, abstractmethod
from PyInquirer import prompt
from datetime import datetime
from pathlib import Path

# Command line application
app = typer.Typer(
    add_completion=False,
    help=__doc__,
    )

DEFAULT_CONFIG_PATH = Path(__file__).parent / 'vao-recorder.yaml'
DEFAULT_CONFIG_PATH_OPTION = typer.Option(
    DEFAULT_CONFIG_PATH,
    help="Path to a `yaml` config file. Run `config` command to generate one."
    )
DEFAULT_OUTPUT_FOLDER = Path(__file__).parent / 'output' / \
    datetime.now().strftime('VAO_%Y-%m-%d_%H-%M-%S')
DEFAULT_OUTPUT_FOLDER_OPTION = typer.Option(
    DEFAULT_OUTPUT_FOLDER,
    help="""
    Path to a folder where the recorded data and the recording configuration
    will be stored."""
    )

# -------------------------------- Utilities -------------------------------- #


def wave_read(filename: Path) -> Tuple[np.ndarray, int]:
    # Utility function that reads the whole `wav` file content into a numpy
    with wave.open(str(filename), 'rb') as f:
        return (
            np.reshape(
                np.frombuffer(
                    f.readframes(f.getnframes()),
                    dtype=f'int{f.getsampwidth()*8}'
                    ), (-1, f.getnchannels())
                ),
            f.getframerate(),
            )


def choose(message: str, choices: list):
    # Utility function that asks the user to configure the devices
    return prompt({
        'type': 'list',
        'name': 'choice',
        'message': message,
        'choices': choices,
        })['choice']


def wait(seconds: int = 4, label: str = 'Recording...', **kwargs):
    with typer.progressbar(range(seconds * 10), label=label, **kwargs) as p:
        for _ in p:
            sd.sleep(100)


def typer_warn(message: str):
    return typer.secho(message, bg='black', fg='yellow')


# ------------------------------ Configuration ------------------------------ #


class Device:

    def __init__(self, find: Callable, name: str) -> None:
        self.find = find
        self.name = name

    @property
    def config_key(self) -> str:
        return self.name.lower()

    # Define which attributes from the device are passed to the `config`
    # dictionary
    config_map = {
        # (key in `config`): (key in `device` or value getter)
        'name': 'name',
        }

    def choose_config(self) -> dict:
        choices = {}
        devices = self.find()
        if not devices:
            typer_warn(f"Could not find {self.name} devices")
            return choices
        while typer.confirm(
            f"Add {'another' if choices else 'a'} {self.name} device?"
            ):
            _id = choose(
                message=f"Select the {self.name} to add to the configuration:",
                choices=[{
                    'name': f"{_id} {d['name']}",
                    'value': _id
                    } for _id, d in devices.items()]
                )
            choices[_id] = {
                k: devices[_id][v] if isinstance(v, str) else v(devices[_id])
                for k, v in self.config_map.items()
                }
        return choices


def find_microphones() -> dict:
    return {
        i: d
        for i, d in enumerate(sd.query_devices())
        if d['max_input_channels'] > 0
        }


Microphone = Device(find_microphones, 'microphone')
Microphone.config_map = {
    'samplerate': lambda device: int(device['default_samplerate']),
    'channels': lambda device: int(device['max_input_channels']),
    **Microphone.config_map,
    }


@app.command(help='Display the available microphones')
def show_microphones(verbose: bool = False):
    devices = Microphone.find()
    if not verbose:
        devices = {i: d['name'] for i, d in devices.items()}
    typer.echo('Microphones:\n' + yaml.dump(devices))


def find_realsense() -> dict:
    devices = {}
    for d in rs.context().query_devices():
        sn = d.get_info(rs.camera_info.serial_number)
        config = rs.config()
        config.enable_device(sn)
        config.enable_all_streams()
        pipeline_profile = config.resolve(rs.pipeline_wrapper(rs.pipeline()))
        streams = {}
        for s in pipeline_profile.get_streams():
            name = s.stream_name()
            streams[name] = {
                'format': str(s.format())[7:],  # remove 'format.'
                'framerate': s.fps(),
                'type': str(s.stream_type())[7:],  # remove 'stream.'
                }
            if s.is_motion_stream_profile():
                streams[name]['intrinsics'] = s.get_motion_intrinsics().data
            elif s.is_video_stream_profile():
                intrinsics = s.get_intrinsics()
                streams[name].update(intrinsics.__dict__)
        devices[sn] = {
            'name': d.get_info(rs.camera_info.name),
            'streams': streams,
            }
    return devices


RealSense = Device(find_realsense, 'RealSense')


@app.command(help='Display the available RealSense devices')
def show_realsense(verbose: bool = False):
    devices = RealSense.find()
    if not verbose:
        devices = {i: d['name'] for i, d in devices.items()}
    print(devices)
    typer.echo('RealSense devices:\n' + yaml.dump(devices))


# def find_cameras(max_index: int = 10) -> dict:
#     return {
#         i: {
#             'cap':
#                 cap,
#             'name':
#                 cv2.videoio_registry.getBackendName(
#                     int(cap.get(cv2.CAP_PROP_BACKEND))
#                     ),
#             'width':
#                 int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
#             'height':
#                 int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
#             }
#         for i in range(max_index) if (cap := cv2.VideoCapture(i)).isOpened()
#         }

# Camera = Device(find_cameras, 'camera')

# @app.command(help='Display the available cameras')
# def show_cameras():
#     # Remove the `cap` attribute from the camera devices
#     devices = {
#         i: {k: v
#             for k, v in camera.items() if k != 'cap'}
#         for i, camera in Camera.find().items()
#         }
#     typer.echo('Real Sense devices:\n' + yaml.dump(devices))


@app.command(help='Create a configuration `yaml` file.')
def config(
        output: Optional[Path] = typer.Option(
            DEFAULT_CONFIG_PATH,
            help="Path to where the configuration yaml file should be written."
            )
    ) -> dict:
    config = {}
    for device in [Microphone, RealSense]:
        config[device.config_key] = device.choose_config()
    with open(output, 'w') as f:
        f.write(yaml.dump(config))
    typer.echo(
        f"Configuration file written to {output}. Remember that it can be "
        "edited manually. Check the repository for an explained example file "
        "https://github.com/AcousticOdometry/VAO-recorder/blob/main/example-config.yaml"
        )
    return config


def get_config(path=DEFAULT_CONFIG_PATH) -> dict:
    _config = None
    if path.exists():
        with open(path, 'r') as f:
            _config = yaml.safe_load(f)
    if not _config:
        typer_warn(f"No configuration found in {path}. Generate one.")
        _config = config(path)
    return _config


# -------------------------------- Recording -------------------------------- #


class Recorder(ABC):

    def __init__(
            self,
            config: dict,  # Configuration dictionary
            output_folder: Path,  # Folder where data should be written
        ):
        self.output_folder = output_folder
        self.devices = config.get(self.device.config_key)

    @property
    @abstractmethod
    def device(self) -> Device:
        # `Device` instance used to get the configuration
        pass

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    def __del__(self):
        self.stop()


class AudioRecorder(Recorder):
    device = Microphone

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for i, (_id, mic) in enumerate(self.devices.items()):
            # Write configuration in a yaml file
            with open(self.output_folder / f'audio{i}.yaml', 'w') as f:
                f.write(yaml.dump(mic))
            # Create audio stream
            name = f"{_id} {mic.pop('name', '')}"
            try:
                self.devices[_id]['stream'] = self._get_stream(
                    device_id=_id,
                    output_path=self.output_folder / f'audio{i}.wav',
                    **mic
                    )
            except Exception as e:
                raise RuntimeError(
                    f'Failed to open microphone `{name}`, review its '
                    f'configuration {mic}\nError: {e}'
                    )

    @staticmethod
    def _get_stream(
        device_id: int,  # Device identifier
        output_path: Path,  # Path to where the audio file should be written
        samplewidth: int = 2,  # Sample width in bytes
        samplerate: int = None,  # Sample rate
        channels: int = None,  # Number of channels
        **stream_kwargs,  # Additional keyword arguments for sd.RawInputStream
        # https://python-sounddevice.readthedocs.io/en/0.4.4/api/streams.html#sounddevice.InputStream
        ) -> sd.InputStream:
        f = wave.open(str(output_path), 'wb')
        f.setnchannels(int(channels))
        f.setframerate(int(samplerate))
        f.setsampwidth(samplewidth)
        return sd.RawInputStream(
            device=device_id,
            dtype=f'int{samplewidth*8}',
            samplerate=samplerate,
            channels=channels,
            callback=lambda data, N, t, status: f.writeframesraw(data),
            finished_callback=f.close,
            **stream_kwargs
            )

    @property
    def streams(self):
        return [m['stream'] for m in self.devices.values() if 'stream' in m]

    def start(self):
        for stream in self.streams:
            stream.start()
        # Write start timestamp
        with open(self.output_folder / 'audio_start.txt', 'w') as f:
            f.write(str(datetime.now().timestamp()))

    def stop(self):
        for stream in self.streams:
            stream.stop()
            stream.close()


class RealSenseRecorder(Recorder):
    device = RealSense

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configs = []
        # Get RealSense camera streams
        for i, (sn, cam) in enumerate(self.devices.items()):
            # Write configuration in a yaml file
            with open(self.output_folder / f'rsdevice{i}.yaml', 'w') as f:
                f.write(yaml.dump(cam))
            config = rs.config()
            config.enable_device(sn)
            config.enable_all_streams()
            config.enable_record_to_file(
                str(self.output_folder / f'rsdevice{i}.bag')
                )
            config.resolve()
            self.configs.append(config)
        self.pipelines = []

    def start(self):
        for config in self.configs:
            pipeline = rs.pipeline()
            pipeline.start(config)
            self.pipelines.append(pipeline)

    def stop(self):
        while self.pipelines:
            pipeline = self.pipelines.pop()
            pipeline.stop()


# class VideoRecorder(Recorder):
#     device = Camera

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         if self.devices:
#             raise NotImplementedError(
#                 'Video recording not implemented yet. Remove cameras from the '
#                 'configuration. Use microphones or RealSense devices instead.'
#                 )

#     def start(self):
#         pass

#     def stop(self):
#         pass


@app.command(help='Record visual and acoustic data.')
def record(
    config_path: Optional[Path] = DEFAULT_CONFIG_PATH_OPTION,
    output_folder: Optional[Path] = DEFAULT_OUTPUT_FOLDER_OPTION,
    ) -> Path:
    config = get_config(config_path)
    output_folder.mkdir(exist_ok=True, parents=True)
    # Setup recording
    recorders = [r(config, output_folder) for r in Recorder.__subclasses__()]
    # Start the recording
    for r in recorders:
        r.start()
    # Wait for user input
    input('Press `Enter` to stop recording.')
    # Cleanup the recording
    for r in recorders:
        r.stop()
    return output_folder


# --------------------------------- Testing --------------------------------- #


@app.command(
    help="""
    Record 5 seconds from the configured microphones and play back the audio of
    each recording."""
    )
def test_microphones(
    config_path: Optional[Path] = DEFAULT_CONFIG_PATH_OPTION,
    output_folder: Optional[Path] = DEFAULT_OUTPUT_FOLDER_OPTION,
    ) -> Path:
    config = get_config(config_path)
    output_folder.mkdir(exist_ok=True, parents=True)
    # Record 5 seconds of audio
    audio = AudioRecorder(config, output_folder)
    audio.start()
    wait(5)
    audio.stop()
    # Play audio
    for _file in output_folder.glob('audio*.wav'):
        typer.echo(f'Playing {_file}')
        with open(_file.with_suffix('.yaml')) as f:
            typer.echo(f.read())
        data, fs = wave_read(_file)
        sd.play(data, samplerate=fs, blocking=True)


@app.command(
    help="""
    Record 5 seconds from the configured cameras. The generated `.bag` files
    need to be manually checked using `ROS` or the RealSense SDK."""
    )
def test_realsense(
    config_path: Optional[Path] = DEFAULT_CONFIG_PATH_OPTION,
    output_folder: Optional[Path] = DEFAULT_OUTPUT_FOLDER_OPTION,
    ) -> Path:
    config = get_config(config_path)
    output_folder.mkdir(exist_ok=True, parents=True)
    # Record 5 seconds of video
    realsense = RealSenseRecorder(config, output_folder)
    realsense.start()
    wait(5)
    realsense.stop()


if __name__ == '__main__':
    # Launch the command line application
    try:
        app()
    except RuntimeError as e:
        typer.secho(str(e), fg='red')