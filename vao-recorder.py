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
import cv2

from abc import ABC, abstractmethod
from typing import Optional, Tuple
from PyInquirer import prompt
from datetime import datetime
from functools import cache
from pathlib import Path

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


# TODO
class Config(dict):

    def __init__(self, path: Path = DEFAULT_CONFIG_PATH):
        if path.exists():
            with open(path, 'r') as f:
                _config = yaml.safe_load(f)
        if not _config:
            typer.secho(
                f'No configuration found in {path}. Generate one.',
                fg='black',
                bg='yellow'
                )
            _config = config(path)
        self.update(**_config)

    @staticmethod
    @cache
    def all_microphones():
        pass

    @staticmethod
    @cache
    def all_real_sense():
        pass

    # ! Checks the first 10 cameras only
    @staticmethod
    @cache
    def all_cameras(max_index: int = 10) -> Tuple[int, dict]:
        print('Searching for cameras...')
        _cameras = {}
        for i in range(max_index):
            if (cap := cv2.VideoCapture(i)).isOpened():
                _cameras[i] = {
                    'cap': cap,
                    'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                    }
        return _cameras


MICROPHONES = {
    i: d
    for i, d in enumerate(sd.query_devices()) if d['max_input_channels'] > 0
    }
REAL_SENSE_DEVICES = {
    d.get_info(rs.camera_info.serial_number): {
        'name': d.get_info(rs.camera_info.name)
        }
    for d in rs.context().query_devices()
    }

# CAMERAS = {
#     i: {
#         'cap': cap,
#         'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
#         'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
#         }
#     for i in range(_MAX_CAMERA_IDX) if (cap := cv2.VideoCapture(i)).isOpened()
#     }


# Utility function that reads the whole `wav` file content into a numpy array
def wave_read(filename: Path) -> Tuple[np.ndarray, int]:
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


@app.command(help='Display the available microphones')
def show_microphones(verbose: bool = False):
    devices = MICROPHONES
    if not verbose:
        devices = {i: d['name'] for i, d in devices.items()}
    typer.echo('Microphones:\n' + yaml.dump(devices))


@app.command(help='Display the available RealSense devices')
def show_real_sense_devices(verbose: bool = False):
    devices = REAL_SENSE_DEVICES
    if not verbose:
        devices = {i: d['name'] for i, d in devices.items()}
    typer.echo('Real Sense devices:\n' + yaml.dump(devices))


@app.command(help='Display the available cameras')
def show_cameras():
    devices = {
        i: {k: v
            for k, v in c.items() if k != 'cap'}
        for i, c in Config.cameras().items()
        }
    print([c for i, c in Config.cameras().items()])
    typer.echo('Real Sense devices:\n' + yaml.dump(devices))


@app.command(help='Create a configuration `yaml` file.')
def config(
        output: Optional[Path] = typer.Option(
            DEFAULT_CONFIG_PATH,
            help="Path to where the configuration yaml file should be written."
            )
    ) -> dict:
    config = {'microphones': {}, 'real_sense_devices': {}}
    while MICROPHONES and typer.confirm(
        f"Add {'another' if config['microphones'] else 'a'} microphone?"
        ):
        device_id = prompt({
            'type':
                'list',
            'name':
                'device_id',
            'message':
                f"Select the microphone to add to the configuration:",
            'choices': [{
                'name': f"{i} {d['name']}",
                'value': i
                } for i, d in MICROPHONES.items()],
            })['device_id']
        config['microphones'][device_id] = {
            'name': MICROPHONES[device_id]['name'],
            'samplerate': int(MICROPHONES[device_id]['default_samplerate']),
            'channels': int(MICROPHONES[device_id]['max_input_channels']),
            }
    while REAL_SENSE_DEVICES and typer.confirm(
        f"Add {'another' if config['real_sense_devices'] else 'a'} "
        "RealSense device?"
        ):
        serial_number = prompt({
            'type':
                'list',
            'name':
                'serial_number',
            'message':
                f"Select the RealSense device to add to the configuration:",
            'choices': [{
                'name': f"{sn} {d['name']}",
                'value': sn
                } for sn, d in REAL_SENSE_DEVICES.items()],
            })['serial_number']
        config['real_sense_devices'][serial_number] = {
            'name': MICROPHONES[device_id]['name'],
            }
    with open(output, 'w') as f:
        f.write(yaml.dump(config))
    return config


def get_config(path=DEFAULT_CONFIG_PATH) -> dict:
    if path.exists():
        with open(path, 'r') as f:
            _config = yaml.safe_load(f)
    if not _config:
        typer.secho(
            f'No configuration found in {path}. Generate one.',
            fg='black',
            bg='yellow'
            )
        _config = config(path)
    return _config


class Recorder(ABC):

    def __init__(
            self,
            config: dict,  # Configuration dictionary
            output_folder: Path,  # Folder where data should be written
        ):
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

    def __init__(self, config: dict, output_folder: Path):
        self.output_folder = output_folder
        self.microphones = config.get('microphones', {})
        for i, (_id, mic) in enumerate(self.microphones.items()):
            # Write configuration in a yaml file
            with open(output_folder / f'audio{i}.yaml', 'w') as f:
                f.write(yaml.dump(mic))
            # Create audio stream
            name = f"{_id} {mic.pop('name', '')}"
            try:
                self.microphones[_id]['stream'] = self._get_stream(
                    device_id=_id,
                    output_path=output_folder / f'audio{i}.wav',
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
        return [
            m['stream'] for m in self.microphones.values() if 'stream' in m
            ]

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

    def __init__(self, config: dict, output_folder: Path):
        self.output_folder = output_folder
        self.devices = config.get('real_sense_devices', {})
        self.configs = []
        # Get RealSense camera streams
        for i, (sn, cam) in enumerate(self.devices.items()):
            # Write configuration in a yaml file
            with open(output_folder / f'rsdevice{i}.yaml', 'w') as f:
                f.write(yaml.dump(cam))
            config = rs.config()
            config.enable_device(sn)
            config.enable_all_streams()
            config.enable_record_to_file(output_folder / f'rsdevice{i}.bag')
            self.configs[i] = config
        self.pipelines = []

    def start(self):
        for config in self.configs:
            pipeline = rs.pipeline()
            pipeline.start(config)
            self.pipelines.append(pipeline)

    def stop(self):
        for pipeline in self.pipelines:
            pipeline.stop()


class VideoRecorder(Recorder):
    pass


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
    with typer.progressbar(range(50), label='Recording...') as progress:
        for _ in progress:
            sd.sleep(100)  # milliseconds
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
def test_real_sense_devices(
    config_path: Optional[Path] = DEFAULT_CONFIG_PATH_OPTION,
    output_folder: Optional[Path] = DEFAULT_OUTPUT_FOLDER_OPTION,
    ) -> Path:
    config = get_config(config_path)
    output_folder.mkdir(exist_ok=True, parents=True)
    # Record 5 seconds of audio
    realsense = RealSenseRecorder(config, output_folder)
    realsense.start()
    with typer.progressbar(range(50), label='Recording...') as progress:
        for _ in progress:
            sd.sleep(100)  # milliseconds
    realsense.stop()


if __name__ == '__main__':
    try:
        app()
    except RuntimeError as e:
        typer.secho(str(e), fg='red')