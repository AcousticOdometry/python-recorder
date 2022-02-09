import sounddevice as sd
import numpy as np
import typer
import yaml
import wave

from typing import Optional, List, Tuple
from PyInquirer import prompt
from datetime import datetime
from pathlib import Path

app = typer.Typer()

DEFAULT_CONFIG_PATH = Path(__file__).parent / 'vao-recorder.yaml'
DEFAULT_OUTPUT_FOLDER = Path(__file__).parent / 'output' / \
    datetime.now().strftime('VAO_%Y-%m-%d_%H-%M-%S')
MICROPHONES = {
    i: d
    for i, d in enumerate(sd.query_devices()) if d['max_input_channels'] > 0
    }


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


@app.command()
def microphones():
    for id, d in MICROPHONES.items():
        typer.echo(f"{id}:\n\tname: {d['name']}")


@app.command(help='Create a configuration `yaml` file.')
def config(
        output: Optional[Path] = typer.Option(
            DEFAULT_CONFIG_PATH,
            help="Path to where the configuration yaml file should be written."
            )
    ) -> dict:
    config = {'microphones': {}, 'cameras': {}}
    while typer.confirm(
        f"Do you want to add {'another' if config['microphones'] else 'a'} "
        "microphone?"
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
            'samplerate': MICROPHONES[device_id]['default_samplerate'],
            'channels': MICROPHONES[device_id]['max_input_channels'],
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


class AudioRecorder:

    def __init__(
            self,
            config: dict,  # Configuration dictionary
            output_folder:
        Path,  # Folder where the audio files should be written
        ):
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

    def __del__(self):
        self.stop()


class VideoRecorder:
    pass


@app.command(help='Record visual and acoustic data.')
def record(
    config_path: Optional[Path] = typer.Option(
        DEFAULT_CONFIG_PATH,
        help="""
        Path to a `yaml` config file. Run `config` command to generate one."""
        ),
    output_folder: Optional[Path] = typer.Option(
        DEFAULT_OUTPUT_FOLDER,
        help="""
        Path to a folder where the recorded data and the recording
        configuration will be stored."""
        ),
    ) -> Path:
    config = get_config(config_path)
    output_folder.mkdir(exist_ok=True, parents=True)
    # Setup audio recording
    audio = AudioRecorder(config, output_folder)
    # Setup video recording
    for camera in config.get('cameras', []):
        # TODO read video cameras
        typer.echo(camera)
    # Start the recording
    audio.start()
    # Wait for user input
    input('Press `Enter` to stop recording.')
    # Cleanup the recording
    audio.stop()
    return output_folder


@app.command(
    help="""
    Record 5 seconds from the configured microphones and play back the audio of
    each recording."""
    )
def test_audio(
    config_path: Optional[Path] = typer.Option(
        DEFAULT_CONFIG_PATH,
        help="""
        Path to a `yaml` config file. Run `config` command to generate one."""
        ),
    output_folder: Optional[Path] = typer.Option(
        DEFAULT_OUTPUT_FOLDER,
        help="""
        Path to a folder where the recorded data and the recording
        configuration will be stored."""
        ),
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


if __name__ == '__main__':
    try:
        app()
    except RuntimeError as e:
        typer.secho(str(e), fg='red')