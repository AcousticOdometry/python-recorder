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

# -------------------------------- Utilities -------------------------------- #



# ------------------------------ Configuration ------------------------------ #








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
    yaml_dump(config, to_file=output)
    typer.echo(
        f"Configuration file written to {output}. Remember that it can be "
        "edited manually. Check the repository for an explained example file "
        "https://github.com/AcousticOdometry/VAO-recorder/blob/main/example-config.yaml"
        )
    return config


def get_config(path=DEFAULT_CONFIG_PATH) -> dict:
    _config = None
    if path.exists():
        _config = yaml_load(path)
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
            yaml_dump(mic, to_file=self.output_folder / f'audio{i}.yaml')
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
        # ! Can this cause delay in starting the video recording?
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
        for i, (sn, device) in enumerate(self.devices.items()):
            # Write configuration in a yaml file
            if not (streams := device.get('streams', [])):
                continue
            yaml_dump(device, to_file=self.output_folder / f'rsdevice{i}.yaml')
            config = rs.config()
            config.enable_device(sn)
            for stream in streams.values():
                parameters = {
                    'stream_type': getattr(rs.stream, stream['type']),
                    'format': getattr(rs.format, stream['format']),
                    'framerate': stream['framerate'],
                    }
                if 'width' in stream:
                    parameters['width'] = stream['width']
                    parameters['height'] = stream['height']
                config.enable_stream(**parameters)
            config.enable_record_to_file(
                str(self.output_folder / f'rsdevice{i}.bag')
                )
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
    recorders = [
        r(config, output_folder) for r in (RealSenseRecorder, AudioRecorder)
        ]
    # Todo pause
    # Start the recording
    for r in recorders:
        r.start()
    # Wait for user input
    input('Press `Enter` to stop recording.')
    # Cleanup the recording
    for r in recorders:
        r.stop()
    typer.echo(f"Recording finished. Output: {output_folder}")
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
        with open(_file.with_suffix('.yaml'), encoding='utf-8') as f:
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
    typer.echo(f"Test output: {output_folder}")


if __name__ == '__main__':
    # Launch the command line application
    try:
        app()
    except RuntimeError as e:
        typer.secho(str(e), fg='red')